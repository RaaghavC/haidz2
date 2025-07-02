"""
Enhanced analyzer with better JavaScript handling and pattern recognition.
"""

import asyncio
from typing import List, Dict, Optional, Any
from playwright.async_api import Page, ElementHandle
from src.models.strategies import AnalysisResult, ElementPattern, DataContainer, NavigationPattern, ElementType
from src.strategies.archive_patterns import get_pattern_for_url, get_wait_strategy
import re


class EnhancedAnalyzer:
    """Enhanced analyzer for real-world archive websites."""
    
    def __init__(self):
        self.min_pattern_occurrences = 2
        self.max_wait_time = 120000  # 2 minutes
        
    async def analyze_page(self, page: Page) -> AnalysisResult:
        """
        Analyze a page with enhanced JavaScript handling.
        """
        url = page.url
        print(f"Analyzing: {url}")
        
        # Get archive-specific patterns
        archive_pattern = get_pattern_for_url(url)
        wait_strategy = get_wait_strategy(url)
        
        # Apply wait strategy
        await self._apply_wait_strategy(page, wait_strategy)
        
        # Take screenshot for debugging
        await page.screenshot(path=f"analysis_{url.replace('/', '_')[:50]}.png")
        
        # Determine page type
        page_type = await self._determine_page_type(page)
        print(f"Page type: {page_type}")
        
        # Find patterns
        element_patterns = await self._find_element_patterns(page, archive_pattern)
        print(f"Found {len(element_patterns)} element patterns")
        
        # Detect data containers
        data_containers = await self._detect_data_containers(page, archive_pattern)
        print(f"Found {len(data_containers)} data containers")
        
        # Analyze navigation
        navigation_pattern = await self._analyze_navigation_patterns(page, archive_pattern)
        
        # If we have many element patterns but no containers, create a virtual container
        if element_patterns and not data_containers:
            # Find the pattern with the most items
            best_pattern = max(element_patterns, key=lambda p: p.count)
            if best_pattern.count >= 10:  # At least 10 items
                # Create a virtual container for this pattern
                virtual_container = DataContainer(
                    selector="body",  # Use body as the container
                    item_selector=best_pattern.selector,
                    sample_count=best_pattern.count,
                    field_selectors={
                        "title": best_pattern.selector,  # Will extract from the item
                        "_item_selector": best_pattern.selector
                    },
                    sample_data=[{"title": best_pattern.sample_text}] if best_pattern.sample_text else [],
                    confidence=0.8  # High confidence since we found many items
                )
                data_containers = [virtual_container]
                print(f"Created virtual container for {best_pattern.count} {best_pattern.selector} items")
        
        # Calculate confidence
        confidence = self._calculate_overall_confidence(
            element_patterns, data_containers, navigation_pattern
        )
        
        return AnalysisResult(
            url=url,
            page_type=page_type,
            element_patterns=element_patterns,
            data_containers=data_containers,
            navigation_pattern=navigation_pattern,
            confidence=confidence
        )
    
    async def _apply_wait_strategy(self, page: Page, strategy: Dict[str, Any]) -> None:
        """Apply intelligent wait strategy that adapts to content loading."""
        try:
            # First, wait for basic page load
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
            
            # Check for dynamic content loading indicators
            await page.wait_for_timeout(1000)  # Brief wait for initial JS
            
            # Look for common loading indicators and wait for them to disappear
            loading_selectors = [
                "[class*='loading']", "[class*='spinner']", "[class*='loader']",
                ".loader", ".loading", ".spinner", ".progress",
                "[aria-label*='loading']", "[aria-label*='Loading']"
            ]
            
            for selector in loading_selectors:
                try:
                    loader = await page.query_selector(selector)
                    if loader:
                        print(f"Found loading indicator: {selector}")
                        # Wait for it to disappear
                        await page.wait_for_function(
                            f"document.querySelector('{selector}') === null || "
                            f"getComputedStyle(document.querySelector('{selector}')).display === 'none'",
                            timeout=15000
                        )
                        print("Loading indicator disappeared")
                        break
                except Exception:
                    continue
            
            # Try to detect when content appears by looking for common patterns
            content_indicators = [
                "[class*='result']", "[class*='item']", "[class*='card']", 
                "[class*='photo']", "[class*='image']", "[class*='gallery']",
                "article", "li:not([class*='nav'])", "img"
            ]
            
            # Wait for content to appear with multiple attempts
            content_found = False
            for attempt in range(3):
                await page.wait_for_timeout(2000)  # Wait a bit more
                
                for selector in content_indicators:
                    try:
                        elements = await page.query_selector_all(selector)
                        if len(elements) >= 2:  # Multiple items suggests content is loaded
                            print(f"Content detected: {len(elements)} {selector} elements")
                            content_found = True
                            break
                    except Exception:
                        continue
                
                if content_found:
                    break
            
            # Try archive-specific selectors
            for selector in strategy.get("wait_selectors", []):
                try:
                    await page.wait_for_selector(selector, timeout=10000, state="visible")
                    print(f"Found expected selector: {selector}")
                    break
                except:
                    continue
            
            # Try network idle as fallback for heavy JS sites
            if not content_found:
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                    print("Network reached idle state")
                except Exception:
                    print("Network idle timeout, using fixed wait...")
                    await page.wait_for_timeout(5000)
            
        except Exception as e:
            print(f"Wait strategy completed with warnings: {e}")
    
    async def _determine_page_type(self, page: Page) -> str:
        """Determine the type of page with enhanced detection."""
        # Check for search/results indicators
        search_indicators = [
            "search", "results", "query", "browse", "discover",
            "collection", "archive", "gallery", "catalog"
        ]
        
        url_lower = page.url.lower()
        for indicator in search_indicators:
            if indicator in url_lower:
                return "listing"
        
        # Check page content
        title = await page.title()
        if title:
            title_lower = title.lower()
            for indicator in search_indicators:
                if indicator in title_lower:
                    return "listing"
        
        # Check for common listing elements
        listing_selectors = [
            "[class*='result']", "[class*='item']", "[class*='card']",
            "[class*='thumbnail']", "[class*='collection']", "[class*='gallery']",
            ".results", ".items", ".listings", "#results"
        ]
        
        for selector in listing_selectors:
            elements = await page.query_selector_all(selector)
            if len(elements) > 2:
                return "listing"
        
        # Check for detail page indicators
        detail_indicators = ["article", ".detail", "#detail", "[class*='detail']"]
        for selector in detail_indicators:
            if await page.query_selector(selector):
                metadata = await page.query_selector_all("[class*='metadata']")
                if len(metadata) > 3:
                    return "detail"
        
        return "unknown"
    
    async def _find_element_patterns(self, page: Page, archive_pattern=None) -> List[ElementPattern]:
        """Find repeating element patterns."""
        patterns = []
        
        # Use archive-specific hints if available
        if archive_pattern:
            selectors_to_check = (
                archive_pattern.container_hints + 
                archive_pattern.item_hints +
                [
                    "[class*='result']", "[class*='item']", "[class*='card']",
                    "[class*='collection']", "[class*='thumbnail']"
                ]
            )
        else:
            selectors_to_check = [
                "[class*='result']", "[class*='item']", "[class*='card']",
                "[class*='collection']", "[class*='thumbnail']", "[class*='photo']",
                "[class*='image']", "[class*='gallery']", "[class*='archive']",
                "article", ".result", ".item", ".card", "li", "tr"
            ]
        
        # Remove duplicates while preserving order
        selectors_to_check = list(dict.fromkeys(selectors_to_check))
        
        for selector in selectors_to_check:
            try:
                elements = await page.query_selector_all(selector)
                count = len(elements)
                
                if count >= self.min_pattern_occurrences:
                    # Get sample text
                    sample_text = ""
                    if elements:
                        try:
                            sample_text = await elements[0].inner_text()
                            sample_text = sample_text[:100] if sample_text else ""
                        except:
                            pass
                    
                    pattern = ElementPattern(
                        selector=selector,
                        element_type=self._determine_element_type(selector),
                        count=count,
                        sample_text=sample_text,
                        confidence=self._calculate_selector_confidence(count)
                    )
                    patterns.append(pattern)
                    print(f"Pattern found: {selector} ({count} items)")
                    
            except Exception as e:
                print(f"Error checking selector {selector}: {e}")
                continue
        
        return patterns
    
    async def _detect_data_containers(self, page: Page, archive_pattern=None) -> List[DataContainer]:
        """Detect containers with enhanced pattern matching."""
        containers = []
        
        # Enhanced container selectors to check - more comprehensive for modern sites
        base_selectors = [
            # Common container patterns
            ".results", ".items", ".container", "#content", "main", "[role='main']",
            ".content-area", "#main-content", ".main-content", ".content",
            
            # Grid and list patterns
            "[class*='grid']", "[class*='list']", "[class*='row']", "[class*='col']",
            "[class*='flex']", "[class*='wrap']", "[class*='container']",
            
            # Gallery and media patterns
            "[class*='gallery']", "[class*='photo']", "[class*='image']", "[class*='thumb']",
            "[class*='thumbnail']", "[class*='media']", "[class*='album']",
            
            # Search and result patterns
            "[class*='result']", "[class*='search']", "[class*='collection']",
            "[class*='archive']", "[class*='browse']", "[class*='catalogue']",
            "[class*='database']", "[class*='record']",
            
            # Modern JS app patterns
            "[id*='app']", "[id*='root']", "#app", "#root",
            ".app", ".application", "[class*='app']", "[class*='component']",
            
            # React/Vue specific
            "[data-reactroot]", "[data-vue]", ".vue-component", ".react-component",
            
            # Generic containers that might hold repeated content
            "section", "article", "div", "ul", "ol", "table", "tbody"
        ]
        
        if archive_pattern:
            container_selectors = archive_pattern.container_hints + base_selectors
        else:
            container_selectors = base_selectors
        
        # Remove duplicates
        container_selectors = list(dict.fromkeys(container_selectors))
        
        for selector in container_selectors:
            container_elem = await page.query_selector(selector)
            if not container_elem:
                continue
            
            # Enhanced child selectors for modern sites
            base_child_selectors = [
                # Item and card patterns  
                "[class*='item']", "[class*='result']", "[class*='card']", "[class*='tile']",
                "[class*='entry']", "[class*='record']", "[class*='element']",
                
                # Media patterns
                "[class*='photo']", "[class*='image']", "[class*='thumbnail']", "[class*='thumb']",
                "[class*='media']", "[class*='picture']", "[class*='gallery-item']",
                
                # Layout patterns
                "[class*='col']", "[class*='cell']", "[class*='box']", "[class*='block']",
                "[class*='panel']", "[class*='section']", "[class*='unit']",
                
                # Collection patterns
                "[class*='collection']", "[class*='archive']", "[class*='specimen']",
                "[class*='artifact']", "[class*='object']", "[class*='asset']",
                
                # Site/work specific patterns
                "[class*='site']", "[class*='work']", "[class*='project']", "[class*='building']",
                "[class*='monument']", "[class*='structure']", "[class*='heritage']",
                
                # Link and content patterns
                "a[href]", "article", "li", "div", "tr", "td",
                "figure", "section", "[role='article']", "[role='listitem']",
                
                # Data attributes that might indicate items (specific ones)
                "[data-id]", "[data-item]", "[data-key]", "[data-index]"
            ]
            
            if archive_pattern:
                child_selectors = archive_pattern.item_hints + base_child_selectors
            else:
                child_selectors = base_child_selectors
            
            for child_selector in child_selectors:
                try:
                    children = await container_elem.query_selector_all(child_selector)
                    
                    if len(children) >= self.min_pattern_occurrences:
                        # Extract field selectors from first few children
                        field_selectors = await self._extract_field_selectors(
                            children[0] if children else container_elem,
                            archive_pattern
                        )
                        
                        # Get sample data
                        sample_data = []
                        for i, child in enumerate(children[:3]):
                            try:
                                item_data = await self._extract_item_data(child, field_selectors)
                                if item_data and any(v for v in item_data.values()):
                                    sample_data.append(item_data)
                            except:
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
                            print(f"Container found: {selector} -> {child_selector} ({len(children)} items)")
                            break
                            
                except Exception as e:
                    print(f"Error checking container {selector}/{child_selector}: {e}")
                    continue
        
        return sorted(containers, key=lambda c: c.confidence, reverse=True)
    
    async def _extract_field_selectors(self, element: ElementHandle, archive_pattern=None) -> Dict[str, str]:
        """Extract field selectors with pattern hints."""
        field_selectors = {}
        
        # Check for label-value patterns
        label_value_patterns = [
            (".field", ".label", ".value"),
            (".metadata-item", ".metadata-label", ".metadata-value"),
            ("[class*='field']", "[class*='label']", "[class*='value']"),
            ("[class*='metadata']", "[class*='label']", "[class*='value']"),
            ("dt", "dt", "dd"),  # Definition lists
            (".property", ".property-label", ".property-value")
        ]
        
        for field_sel, label_sel, value_sel in label_value_patterns:
            fields = await element.query_selector_all(field_sel)
            if fields and len(fields) > 2:
                sample_count = 0
                for field in fields[:5]:
                    try:
                        if field_sel == "dt":  # Special handling for definition lists
                            label_elem = field
                            # Find next dd sibling
                            value_elem = await field.evaluate_handle("el => el.nextElementSibling")
                            if value_elem:
                                tag = await value_elem.evaluate("el => el.tagName")
                                if tag.lower() == "dd":
                                    sample_count += 1
                        else:
                            label_elem = await field.query_selector(label_sel)
                            value_elem = await field.query_selector(value_sel)
                            if label_elem and value_elem:
                                sample_count += 1
                    except:
                        pass
                
                if sample_count >= 2:
                    field_selectors["_structure_type"] = "label-value"
                    field_selectors["_field_selector"] = field_sel
                    field_selectors["_label_selector"] = label_sel
                    field_selectors["_value_selector"] = value_sel
                    return field_selectors
        
        # Use archive-specific mappings if available (only valid CSS selectors)
        if archive_pattern and archive_pattern.metadata_mappings:
            for field_name, selectors in archive_pattern.metadata_mappings.items():
                for selector in selectors:
                    # Skip invalid CSS selectors (text patterns like "Type:")
                    if ":" in selector and not selector.startswith("[") and not selector.startswith(".") and not selector.startswith("#"):
                        continue
                    try:
                        elem = await element.query_selector(selector)
                        if elem:
                            field_selectors[field_name] = selector
                            break
                    except Exception:
                        # Invalid selector, skip it
                        continue
        else:
            # Generic field patterns
            field_patterns = [
                ("title", ["h1", "h2", "h3", "h4", ".title", "[class*='title']", "a"]),
                ("image", ["img", "img[src]", "[class*='image']", "[class*='photo']"]),
                ("date", [".date", "[class*='date']", "time", "[class*='year']"]),
                ("location", [".location", "[class*='location']", "[class*='place']"]),
                ("description", [".description", "[class*='desc']", "p"]),
                ("link", ["a[href]", ".link"])
            ]
            
            for field_name, selectors in field_patterns:
                for selector in selectors:
                    elem = await element.query_selector(selector)
                    if elem:
                        field_selectors[field_name] = selector
                        break
        
        return field_selectors
    
    async def _extract_item_data(self, element: ElementHandle, field_selectors: Dict[str, str]) -> Dict[str, str]:
        """Extract data from an element."""
        data = {}
        
        # Handle label-value structure
        if field_selectors.get("_structure_type") == "label-value":
            field_sel = field_selectors.get("_field_selector", ".field")
            label_sel = field_selectors.get("_label_selector", ".label")
            value_sel = field_selectors.get("_value_selector", ".value")
            
            fields = await element.query_selector_all(field_sel)
            for field in fields:
                try:
                    if field_sel == "dt":  # Definition list
                        label_elem = field
                        value_elem = await field.evaluate_handle("el => el.nextElementSibling")
                        if value_elem:
                            tag = await value_elem.evaluate("el => el.tagName")
                            if tag.lower() == "dd":
                                label = await label_elem.inner_text()
                                value = await value_elem.inner_text()
                                label = label.strip().rstrip(':').lower().replace(' ', '_')
                                data[label] = value.strip()
                    else:
                        label_elem = await field.query_selector(label_sel)
                        value_elem = await field.query_selector(value_sel)
                        if label_elem and value_elem:
                            label = await label_elem.inner_text()
                            value = await value_elem.inner_text()
                            label = label.strip().rstrip(':').lower().replace(' ', '_')
                            data[label] = value.strip()
                except:
                    continue
        
        # Extract other fields
        for field_name, selector in field_selectors.items():
            if field_name.startswith("_"):
                continue
                
            try:
                elem = await element.query_selector(selector)
                if elem:
                    if field_name == "image":
                        data[field_name] = await elem.get_attribute("src") or await elem.get_attribute("data-src")
                    elif field_name == "link":
                        data[field_name] = await elem.get_attribute("href")
                    else:
                        text = await elem.inner_text()
                        data[field_name] = text.strip() if text else None
            except:
                continue
        
        # Try to extract title from link if not found
        if "title" not in data:
            link_elem = await element.query_selector("a")
            if link_elem:
                title = await link_elem.inner_text()
                if title and title.strip():
                    data["title"] = title.strip()
        
        return data
    
    async def _analyze_navigation_patterns(self, page: Page, archive_pattern=None) -> Optional[NavigationPattern]:
        """Analyze navigation with pattern hints."""
        # Use archive-specific hints
        if archive_pattern and archive_pattern.navigation_hints:
            # Check for pagination
            for selector in archive_pattern.navigation_hints.get("pagination", []):
                pagination_elem = await page.query_selector(selector)
                if pagination_elem:
                    return NavigationPattern(
                        type="pagination",
                        pagination_selector=selector,
                        next_selector=archive_pattern.navigation_hints.get("next", [""])[0]
                    )
        
        # Generic pagination patterns
        pagination_selectors = [
            ".pagination", ".pager", "[class*='pagination']",
            "[class*='pager']", "nav[aria-label*='pagination']",
            "[role='navigation']"
        ]
        
        for selector in pagination_selectors:
            elem = await page.query_selector(selector)
            if elem:
                # Look for next button
                next_selectors = [
                    "a:has-text('Next')", "a:has-text('>')", 
                    ".next", "[class*='next']", "a[rel='next']",
                    "button:has-text('Next')"
                ]
                
                for next_sel in next_selectors:
                    next_elem = await page.query_selector(next_sel)
                    if next_elem:
                        return NavigationPattern(
                            type="pagination",
                            pagination_selector=selector,
                            next_selector=next_sel
                        )
        
        # Check for infinite scroll
        scroll_height = await page.evaluate("document.body.scrollHeight")
        viewport_height = await page.evaluate("window.innerHeight")
        
        if scroll_height > viewport_height * 3:
            return NavigationPattern(
                type="infinite_scroll",
                total_pages=None
            )
        
        return None
    
    def _determine_element_type(self, selector: str) -> ElementType:
        """Determine element type from selector."""
        selector_lower = selector.lower()
        
        if any(x in selector_lower for x in ["container", "list", "results", "grid"]):
            return ElementType.DATA_CONTAINER
        elif any(x in selector_lower for x in ["nav", "pag", "page"]):
            return ElementType.NAVIGATION
        elif any(x in selector_lower for x in ["detail", "link", "href"]):
            return ElementType.DETAIL_LINK
        else:
            return ElementType.METADATA
    
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
        field_score = min(field_count / 5.0, 1.0)
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
            scores.append(0.8)
        
        return sum(scores) / len(scores) if scores else 0.0