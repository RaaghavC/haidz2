"""Analyzer module for DOM inspection and pattern recognition."""

import re
from typing import List, Dict, Optional, Any, Set
from collections import Counter
from playwright.async_api import Page, ElementHandle

from src.models.strategies import (
    AnalysisResult, ElementPattern, DataContainer,
    NavigationPattern, ElementType
)


class Analyzer:
    """Analyzes webpage DOM to identify patterns and data structures."""
    
    def __init__(self):
        """Initialize the Analyzer."""
        self.min_pattern_occurrences = 2
        self.confidence_threshold = 0.5
    
    async def analyze_page(self, page: Page) -> AnalysisResult:
        """
        Analyze a webpage and identify its structure.
        
        Args:
            page: Playwright page object
            
        Returns:
            AnalysisResult containing identified patterns
        """
        # Determine page type
        page_type = await self._determine_page_type(page)
        
        # Identify patterns
        element_patterns = await self.identify_repeating_elements(page)
        data_containers = await self.detect_data_containers(page)
        navigation_pattern = await self.analyze_navigation_patterns(page)
        
        # Calculate overall confidence
        confidence = self._calculate_overall_confidence(
            element_patterns, data_containers, navigation_pattern
        )
        
        return AnalysisResult(
            url=page.url,
            page_type=page_type,
            element_patterns=element_patterns,
            data_containers=data_containers,
            navigation_pattern=navigation_pattern,
            metadata={
                "title": await page.title(),
                "element_count": len(element_patterns),
                "container_count": len(data_containers)
            },
            confidence=confidence
        )
    
    async def identify_repeating_elements(self, page: Page) -> List[ElementPattern]:
        """
        Identify repeating elements that might contain data.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of identified element patterns
        """
        patterns = []
        
        # Common selectors for data containers
        common_selectors = [
            ".item", ".record", ".entry", ".result",
            ".card", ".listing", ".product", ".article",
            "[class*='item']", "[class*='record']", "[class*='entry']",
            "article", "li", "tr"
        ]
        
        for selector in common_selectors:
            elements = await page.query_selector_all(selector)
            
            if len(elements) >= self.min_pattern_occurrences:
                # Analyze element structure
                sample_element = elements[0] if elements else None
                sample_text = await sample_element.inner_text() if sample_element else ""
                # Handle mock objects properly
                if hasattr(sample_text, '__await__'):
                    sample_text = await sample_text
                sample_text = str(sample_text)
                
                pattern = ElementPattern(
                    selector=selector,
                    element_type=ElementType.DATA_CONTAINER,
                    count=len(elements),
                    attributes={},
                    sample_text=sample_text[:100],
                    confidence=self._calculate_selector_confidence(len(elements))
                )
                patterns.append(pattern)
        
        # Sort by count and confidence
        patterns.sort(key=lambda p: (p.count, p.confidence), reverse=True)
        
        return patterns
    
    async def detect_data_containers(self, page: Page) -> List[DataContainer]:
        """
        Detect containers that hold structured data.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of identified data containers
        """
        containers = []
        
        # Look for container patterns
        container_selectors = [
            ".item-list", ".results", ".container", ".content",
            ".listings", ".grid", ".table", "tbody",
            "[class*='list']", "[class*='results']", "main", "section",
            ".collection-items", "[class*='collection']", "[class*='archive']"
        ]
        
        for selector in container_selectors:
            container_elem = await page.query_selector(selector)
            if not container_elem:
                continue
            
            # Find repeating children
            child_selectors = [
                "div", "article", "li", "tr", ".item", ".record",
                ".archive-record", "[class*='record']", "[class*='item']"
            ]
            
            for child_selector in child_selectors:
                children = await container_elem.query_selector_all(child_selector)
                
                if len(children) >= self.min_pattern_occurrences:
                    # Extract field selectors from first child
                    field_selectors = await self._extract_field_selectors(children[0])
                    
                    # Get sample data
                    sample_data = []
                    for i, child in enumerate(children[:3]):  # First 3 items
                        try:
                            item_data = await self._extract_item_data(child, field_selectors)
                            if item_data:
                                sample_data.append(item_data)
                        except Exception:
                            # Skip problematic items during testing
                            continue
                    
                    if field_selectors and sample_data:
                        container = DataContainer(
                            selector=selector,
                            item_selector=child_selector,
                            field_selectors=field_selectors,
                            sample_data=sample_data,
                            confidence=self._calculate_container_confidence(
                                len(children), len(field_selectors)
                            )
                        )
                        containers.append(container)
                        break  # Found good container, move to next
        
        # Sort by confidence
        containers.sort(key=lambda c: c.confidence, reverse=True)
        
        return containers
    
    async def analyze_navigation_patterns(self, page: Page) -> Optional[NavigationPattern]:
        """
        Analyze navigation patterns on the page.
        
        Args:
            page: Playwright page object
            
        Returns:
            NavigationPattern if found, None otherwise
        """
        # Check for pagination
        pagination_elem = await page.query_selector(".pagination, .pager, nav[aria-label*='pagination']")
        
        if pagination_elem:
            # Look for next button
            next_button = await page.query_selector(
                ".next, .next-page, a[rel='next'], button:has-text('Next')"
            )
            
            # Look for page numbers
            page_links = await page.query_selector_all(
                ".page-link, .page-number, a[href*='page=']"
            )
            
            # Try to determine current page
            current_page = None
            current_elem = await page.query_selector(".current, .active, [aria-current='page']")
            if current_elem:
                text = await current_elem.inner_text()
                try:
                    current_page = int(re.search(r'\d+', text).group())
                except:
                    current_page = None
            
            return NavigationPattern(
                type="pagination",
                next_selector=".next-page" if next_button else None,
                pagination_selector=".pagination",
                total_pages=len(page_links) if page_links else None,
                current_page=current_page
            )
        
        # Check for infinite scroll
        scroll_indicator = await page.query_selector(
            "[data-infinite-scroll], .infinite-scroll, .load-more"
        )
        
        if scroll_indicator:
            return NavigationPattern(
                type="infinite_scroll",
                pagination_selector=None,
                next_selector=None
            )
        
        # Check for simple next/prev
        next_link = await page.query_selector("a:has-text('Next'), a:has-text('»')")
        prev_link = await page.query_selector("a:has-text('Previous'), a:has-text('«')")
        
        if next_link or prev_link:
            return NavigationPattern(
                type="next_prev",
                next_selector="a:has-text('Next')" if next_link else None,
                pagination_selector=None
            )
        
        return None
    
    async def _determine_page_type(self, page: Page) -> str:
        """Determine the type of page (listing, detail, etc.)."""
        url = page.url.lower()
        
        # URL patterns
        if any(pattern in url for pattern in ["item/", "detail/", "show/", "/id/"]):
            return "detail"
        elif any(pattern in url for pattern in ["list", "search", "browse", "collection"]):
            return "listing"
        
        # Check for repeating elements (listing indicator)
        common_item_selectors = [".item", ".record", ".result", "article"]
        for selector in common_item_selectors:
            items = await page.query_selector_all(selector)
            if len(items) > 3:
                return "listing"
        
        # Check for detail page indicators
        if await page.query_selector("h1"):
            # Look for metadata patterns
            metadata = await page.query_selector_all(".metadata, .field, .property")
            if len(metadata) > 3:
                return "detail"
        
        return "unknown"
    
    async def _extract_field_selectors(self, element: ElementHandle) -> Dict[str, str]:
        """Extract field selectors from a data element."""
        field_selectors = {}
        
        # First check for label-value patterns
        label_value_patterns = [
            (".field", ".label", ".value"),
            (".metadata-item", ".metadata-label", ".metadata-value"),
            ("[class*='field']", "[class*='label']", "[class*='value']"),
            ("[class*='metadata']", "[class*='label']", "[class*='value']")
        ]
        
        for field_sel, label_sel, value_sel in label_value_patterns:
            fields = await element.query_selector_all(field_sel)
            if fields and len(fields) > 3:
                # Sample a few fields to confirm structure
                sample_count = 0
                for field in fields[:5]:  # Check first 5 fields
                    label_elem = await field.query_selector(label_sel)
                    value_elem = await field.query_selector(value_sel)
                    if label_elem and value_elem:
                        sample_count += 1
                
                if sample_count >= 3:
                    # This is a label-value structure
                    field_selectors["_structure_type"] = "label-value"
                    field_selectors["_field_selector"] = field_sel
                    field_selectors["_label_selector"] = label_sel
                    field_selectors["_value_selector"] = value_sel
                    return field_selectors
        
        # Fallback to common field patterns
        field_patterns = [
            ("title", [".title", "h1", "h2", "h3", ".name", "[class*='title']"]),
            ("creator", [".creator", ".artist", ".author", ".photographer", "[class*='creator']"]),
            ("date", [".date", ".year", "time", "[class*='date']"]),
            ("description", [".description", ".desc", ".summary", "[class*='desc']"]),
            ("link", ["a[href]", ".link", ".detail-link"])
        ]
        
        for field_name, selectors in field_patterns:
            for selector in selectors:
                elem = await element.query_selector(selector)
                if elem:
                    field_selectors[field_name] = selector
                    break
        
        return field_selectors
    
    async def _extract_item_data(self, element: ElementHandle, 
                                 field_selectors: Dict[str, str]) -> Dict[str, str]:
        """Extract data from an element using field selectors."""
        data = {}
        
        # Check if this is a label-value structure
        if field_selectors.get("_structure_type") == "label-value":
            field_sel = field_selectors.get("_field_selector", ".field")
            label_sel = field_selectors.get("_label_selector", ".label")
            value_sel = field_selectors.get("_value_selector", ".value")
            
            fields = await element.query_selector_all(field_sel)
            for field in fields:
                try:
                    label_elem = await field.query_selector(label_sel)
                    value_elem = await field.query_selector(value_sel)
                    
                    if label_elem and value_elem:
                        label = await label_elem.inner_text()
                        value = await value_elem.inner_text()
                        
                        # Clean up label
                        label = label.strip().rstrip(':').lower()
                        value = value.strip()
                        
                        # Store with normalized field name
                        field_name = label.replace(' ', '_').replace('.', '')
                        # Keep # for inventory number
                        if 'inventory' not in field_name:
                            field_name = field_name.replace('#', '')
                        data[field_name] = value
                except:
                    continue
            
            # Also try to extract title from common title elements
            title_selectors = [".record-title", ".title", "h1", "h2", "h3", "[class*='title']"]
            for title_sel in title_selectors:
                title_elem = await element.query_selector(title_sel)
                if title_elem:
                    title_text = await title_elem.inner_text()
                    if title_text:
                        data["title"] = title_text.strip()
                        break
        else:
            # Use regular selector-based extraction
            for field_name, selector in field_selectors.items():
                if field_name.startswith("_"):
                    continue
                    
                try:
                    field_elem = await element.query_selector(selector)
                    if field_elem:
                        if field_name == "link":
                            data[field_name] = await field_elem.get_attribute("href")
                        else:
                            text = await field_elem.inner_text()
                            data[field_name] = text.strip()
                except:
                    continue
        
        return data
    
    def _calculate_selector_confidence(self, count: int) -> float:
        """Calculate confidence based on element count."""
        if count < 2:
            return 0.0
        elif count < 5:
            return 0.5
        elif count < 10:
            return 0.7
        elif count < 50:
            return 0.8
        else:
            return 0.9
    
    def _calculate_container_confidence(self, item_count: int, field_count: int) -> float:
        """Calculate confidence for a data container."""
        count_score = self._calculate_selector_confidence(item_count)
        field_score = min(field_count / 5.0, 1.0)  # Expect at least 5 fields
        
        return (count_score + field_score) / 2.0
    
    def _calculate_overall_confidence(self, patterns: List[ElementPattern],
                                      containers: List[DataContainer],
                                      navigation: Optional[NavigationPattern]) -> float:
        """Calculate overall analysis confidence."""
        scores = []
        
        if patterns:
            scores.append(max(p.confidence for p in patterns))
        
        if containers:
            scores.append(max(c.confidence for c in containers))
        
        if navigation:
            scores.append(0.8)  # Navigation found
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _calculate_pattern_confidence(self, elements: List[Dict[str, Any]]) -> float:
        """Calculate confidence based on element consistency."""
        if not elements:
            return 0.0
        
        # Check structural consistency
        child_counts = [e.get("children", 0) for e in elements]
        
        if not child_counts:
            return 0.5
        
        # Calculate variance
        avg_children = sum(child_counts) / len(child_counts)
        variance = sum((c - avg_children) ** 2 for c in child_counts) / len(child_counts)
        
        # Lower variance = higher confidence
        if variance < 0.5:
            return 0.9
        elif variance < 2.0:
            return 0.7
        elif variance < 5.0:
            return 0.5
        else:
            return 0.3
    
    async def _detect_pagination_type(self, page: Page) -> str:
        """Detect the type of pagination used."""
        content = await page.content()
        
        # Check for infinite scroll first (most specific)
        if re.search(r'infinite[-_]?scroll|load[-_]?more|data-infinite', content, re.I):
            return "infinite_scroll"
        
        # Check for next/prev without numbers
        if (re.search(r'class="next"|next[-_]?page|previous|prev[-_]?page', content, re.I) and
            not re.search(r'page[=\-]\d+|/\d+\?|class="page-\w+"', content, re.I)):
            return "next_prev"
        
        # Check for numbered pagination
        if re.search(r'page[=\-]\d+|/\d+\?|class="page-\w+"|pagination.*\d+', content, re.I):
            return "numbered"
        
        return "none"