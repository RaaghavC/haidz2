"""Executor module for Playwright-based scraping execution."""

import asyncio
from typing import List, Dict, Optional, Any
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from src.models.schemas import ArchiveRecord
from src.models.strategies import ScrapingStrategy, FieldMapping, NavigationStrategy
from src.utils.browser_manager import BrowserManager


class Executor:
    """Executes scraping strategies using Playwright."""
    
    def __init__(self, browser_manager: Optional[BrowserManager] = None):
        """Initialize the Executor."""
        self.browser_manager = browser_manager or BrowserManager()
        self.retry_on_missing = False
        self.max_retries = 3
        self._scroll_count = 0
    
    async def execute_strategy(self, strategy: ScrapingStrategy) -> List[Dict[str, Any]]:
        """
        Execute a scraping strategy and extract data.
        
        Args:
            strategy: The scraping strategy to execute
            
        Returns:
            List of extracted data records
        """
        all_data = []
        
        try:
            async with self.browser_manager.create_page() as page:
                # Navigate to URL
                await self._navigate_to_url(page, strategy.url)
                
                # Apply wait conditions
                await self._apply_wait_conditions(page, strategy.wait_conditions)
                
                # Use container selector from strategy or auto-detect
                container_selector = strategy.container_selector
                if not container_selector:
                    container_selector = await self._determine_container_selector(
                        page, strategy.field_mapping
                    )
                
                # Extract data from pages
                page_count = 0
                max_pages = strategy.navigation_strategy.parameters.get("max_pages", 100)
                
                while page_count < max_pages:
                    # Extract data from current page
                    page_data = await self.extract_page_data(
                        page, strategy.field_mapping, container_selector, strategy.item_selector
                    )
                    all_data.extend(page_data)
                    
                    page_count += 1
                    
                    # Try to navigate to next page
                    has_next = await self.navigate_to_next(
                        page, strategy.navigation_strategy
                    )
                    
                    if not has_next:
                        break
                    
                    # Wait for new content to load
                    await self._apply_wait_conditions(page, strategy.wait_conditions)
        
        except Exception as e:
            # Log error and return what we have
            print(f"Error during execution: {e}")
            # In production, use proper logging
        
        finally:
            await self.browser_manager.stop()
        
        return all_data
    
    async def extract_page_data(self, page: Page, field_mapping: FieldMapping,
                                container_selector: Optional[str] = None,
                                item_selector: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract data from the current page.
        
        Args:
            page: Playwright page object
            field_mapping: Field to selector mappings
            container_selector: Selector for data containers
            item_selector: Selector for individual items within containers
            
        Returns:
            List of extracted records
        """
        data = []
        
        # Find containers
        if container_selector:
            containers = await page.query_selector_all(container_selector)
            
            # Extract items from containers
            items = []
            for container in containers:
                if item_selector:
                    container_items = await container.query_selector_all(item_selector)
                    items.extend(container_items)
                else:
                    # Container itself is the item
                    items.append(container)
        else:
            # Try to auto-detect
            container_selector = await self._determine_container_selector(page, field_mapping)
            items = await page.query_selector_all(container_selector) if container_selector else []
        
        # Extract data from each item
        for item in items:
            item_data = await self._extract_single_item(item, field_mapping.mappings)
            if item_data and any(v is not None for v in item_data.values()):
                data.append(item_data)
        
        return data
    
    async def navigate_to_next(self, page: Page, nav_strategy: NavigationStrategy) -> bool:
        """
        Navigate to the next page based on strategy.
        
        Args:
            page: Playwright page object
            nav_strategy: Navigation strategy
            
        Returns:
            True if navigation successful, False otherwise
        """
        if nav_strategy.method == "none":
            return False
        
        elif nav_strategy.method == "click_next":
            next_selector = nav_strategy.selectors.get("next")
            if not next_selector:
                return False
            
            try:
                next_button = await page.query_selector(next_selector)
                if not next_button:
                    return False
                
                await next_button.click()
                
                # Wait after click
                wait_time = nav_strategy.parameters.get("wait_after_click", 2000)
                await page.wait_for_timeout(wait_time)
                
                return True
                
            except Exception:
                return False
        
        elif nav_strategy.method == "scroll":
            # Check if we've reached max scrolls
            max_scrolls = nav_strategy.parameters.get("max_scrolls", 50)
            if self._scroll_count >= max_scrolls:
                self._scroll_count = 0  # Reset for next execution
                return False
            
            # Get current scroll position
            scroll_info = await page.evaluate("""
                () => ({
                    scrollTop: window.pageYOffset || document.documentElement.scrollTop,
                    scrollHeight: document.documentElement.scrollHeight
                })
            """)
            
            # Check if at bottom
            if scroll_info["scrollTop"] >= scroll_info["scrollHeight"] - 1000:
                self._scroll_count = 0  # Reset
                return False
            
            # Scroll down
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            
            # Wait for content to load
            pause_time = nav_strategy.parameters.get("scroll_pause_time", 2000)
            await page.wait_for_timeout(pause_time)
            
            self._scroll_count += 1
            return True
        
        return False
    
    async def _extract_single_item(self, element, field_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract data from a single item element.
        
        Args:
            element: Page element to extract from
            field_mapping: Map of field names to selectors
            
        Returns:
            Dictionary of extracted data
        """
        data = {}
        
        # Check if this is a label-value structure
        if any(selector.startswith("_label_value:") for selector in field_mapping.values()):
            # Extract all label-value pairs first
            label_value_data = {}
            
            # Try different label-value patterns
            patterns = [
                (".field", ".label", ".value"),
                (".metadata-item", ".metadata-label", ".metadata-value"),
                ("[class*='field']", "[class*='label']", "[class*='value']"),
                ("[class*='metadata']", "[class*='label']", "[class*='value']")
            ]
            
            fields_found = False
            for field_sel, label_sel, value_sel in patterns:
                fields = await element.query_selector_all(field_sel)
                if fields:
                    fields_found = True
                    for field in fields:
                        try:
                            label_elem = await field.query_selector(label_sel)
                            value_elem = await field.query_selector(value_sel)
                            
                            if label_elem and value_elem:
                                label = await label_elem.inner_text()
                                value = await value_elem.inner_text()
                                
                                # Clean up
                                label = label.strip().rstrip(':').lower().replace(' ', '_').replace('.', '')
                                # Keep # for inventory number
                                if 'inventory' not in label:
                                    label = label.replace('#', '')
                                value = value.strip()
                                
                                label_value_data[label] = value
                        except:
                            continue
                    break  # Found fields, no need to try other patterns
            
            # Also try to extract title from common title elements
            title_selectors = [".record-title", ".title", "h1", "h2", "h3", "[class*='title']"]
            for title_sel in title_selectors:
                title_elem = await element.query_selector(title_sel)
                if title_elem:
                    title_text = await title_elem.inner_text()
                    if title_text:
                        label_value_data["title"] = title_text.strip()
                        break
            
            # Now map to schema fields
            for field_name, selector in field_mapping.items():
                if selector.startswith("_label_value:"):
                    web_field = selector.replace("_label_value:", "")
                    data[field_name] = label_value_data.get(web_field)
                else:
                    data[field_name] = None
            
            return data
        
        # Regular selector-based extraction
        for field_name, selector in field_mapping.items():
            try:
                field_elem = await element.query_selector(selector)
                
                if field_elem:
                    # Handle different element types
                    tag_name = await field_elem.evaluate("el => el.tagName.toLowerCase()")
                    
                    if tag_name == "a":
                        # Extract href for links
                        value = await field_elem.get_attribute("href")
                    elif tag_name == "img":
                        # Extract src for images
                        value = await field_elem.get_attribute("src")
                    else:
                        # Extract text content
                        value = await field_elem.inner_text()
                        if value:
                            value = value.strip()
                            # Clean up common label patterns
                            if ":" in value:
                                # Extract value after label (e.g., "Date: 2019-05-15" -> "2019-05-15")
                                parts = value.split(":", 1)
                                if len(parts) == 2:
                                    value = parts[1].strip()
                        else:
                            value = None
                    
                    data[field_name] = value
                else:
                    data[field_name] = None
                    
            except Exception:
                data[field_name] = None
        
        return data
    
    async def _navigate_to_url(self, page: Page, url: str) -> None:
        """Navigate to URL with error handling."""
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except PlaywrightTimeout:
            # Try again with longer timeout
            await page.goto(url, wait_until="networkidle", timeout=120000)
    
    async def _apply_wait_conditions(self, page: Page, conditions: List[str]) -> None:
        """Apply wait conditions before extraction."""
        for condition in conditions:
            if condition.startswith("selector:"):
                selector = condition.replace("selector:", "")
                try:
                    await page.wait_for_selector(selector, timeout=10000)
                except:
                    pass  # Continue even if selector not found
            
            elif condition.startswith("timeout:"):
                timeout = int(condition.replace("timeout:", ""))
                await page.wait_for_timeout(timeout)
            
            elif condition == "domcontentloaded":
                # Already handled in navigation
                pass
    
    async def _determine_container_selector(self, page: Page, 
                                            field_mapping: FieldMapping) -> Optional[str]:
        """
        Try to determine the best container selector.
        
        Args:
            page: Playwright page object
            field_mapping: Field mappings to help identify containers
            
        Returns:
            Best guess for container selector
        """
        # Common container selectors to try
        candidates = [
            "div", "article", "li", ".item", ".record", ".entry",
            ".result", ".card", ".listing", "tr", "section"
        ]
        
        best_selector = None
        max_count = 0
        
        for selector in candidates:
            try:
                elements = await page.query_selector_all(selector)
                
                # Check if elements contain expected fields
                if len(elements) > max_count and len(elements) > 1:
                    # Sample first element
                    if elements:
                        sample = elements[0]
                        field_count = 0
                        
                        # Check how many fields can be found
                        for field_selector in field_mapping.mappings.values():
                            elem = await sample.query_selector(field_selector)
                            if elem:
                                field_count += 1
                        
                        # If this container has more fields, use it
                        if field_count > 0:
                            max_count = len(elements)
                            best_selector = selector
            
            except:
                continue
        
        return best_selector