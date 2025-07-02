"""
Enhanced executor with better JavaScript handling and real-world scraping capabilities.
"""

import asyncio
from typing import List, Dict, Any, Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from src.models.strategies import ScrapingStrategy, FieldMapping, NavigationStrategy
from src.utils.browser_manager import BrowserManager
from src.strategies.archive_patterns import get_pattern_for_url, get_wait_strategy
import re
from bs4 import BeautifulSoup


class EnhancedExecutor:
    """Enhanced executor for real-world archive scraping."""
    
    def __init__(self):
        self.browser_manager = BrowserManager()
        self.max_retries = 3
        self.screenshot_count = 0
        
    async def execute_strategy(self, strategy: ScrapingStrategy, page: Optional[Page] = None) -> List[Dict[str, Any]]:
        """
        Execute scraping strategy with enhanced error handling.
        """
        all_data = []
        archive_pattern = get_pattern_for_url(strategy.url)
        
        # Use provided page or create new one
        should_close_page = False
        if page is None:
            page = await self.browser_manager.create_page()
            should_close_page = True
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
        try:
            # Navigate only if not already on the page
            current_url = page.url
            print(f"Current URL: {current_url}, Strategy URL: {strategy.url}")
            if not current_url or not current_url.startswith(strategy.url.rstrip('/')):
                await self._navigate_with_retry(page, strategy.url)
                
            # Take initial screenshot
            await self._take_screenshot(page, "initial")
            
            # Check for export functionality first
            if archive_pattern and archive_pattern.export_available:
                export_data = await self._try_export(page, archive_pattern)
                if export_data:
                    print(f"Used export functionality: {len(export_data)} records")
                    return export_data
            
            # Extract data from pages
            page_count = 0
            max_pages = strategy.navigation_strategy.parameters.get("max_pages", 100)
            
            while page_count < max_pages:
                print(f"\nProcessing page {page_count + 1}")
                
                # Wait for content to load
                await self._wait_for_content(page, archive_pattern)
                
                # Extract data from current page
                page_data = await self._extract_page_data(
                    page, strategy, archive_pattern
                )
                
                if page_data:
                    all_data.extend(page_data)
                    print(f"Extracted {len(page_data)} items from page {page_count + 1}")
                else:
                    print(f"No data extracted from page {page_count + 1}")
                    # Try scrolling if no data found
                    if page_count == 0:
                        await self._try_scroll_loading(page)
                        page_data = await self._extract_page_data(
                            page, strategy, archive_pattern
                        )
                        if page_data:
                            all_data.extend(page_data)
                
                page_count += 1
                
                # Check if we should continue
                if not await self._should_continue(all_data, page_count, max_pages):
                    break
                
                # Navigate to next page
                if strategy.navigation_strategy.method != "none":
                    has_next = await self._navigate_to_next(
                        page, strategy.navigation_strategy, archive_pattern
                    )
                    
                    if not has_next:
                        print("No more pages found")
                        break
                    
                    # Wait for new content
                    await asyncio.sleep(2)
                    
        except Exception as e:
            print(f"Error during execution: {e}")
            await self._take_screenshot(page, "error", force=True)
            
        finally:
            if should_close_page:
                await page.close()
        
        return all_data
    
    async def _navigate_with_retry(self, page: Page, url: str) -> None:
        """Navigate to URL with retry logic."""
        for attempt in range(self.max_retries):
            try:
                print(f"Navigating to {url} (attempt {attempt + 1})")
                wait_strategy = get_wait_strategy(url)
                
                # Special handling for potentially bot-protected sites
                if "archnet.org" in url:
                    print("Using special handling for ArchNet...")
                    # First try with domcontentloaded
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=120000)
                    # Then wait for content
                    await page.wait_for_timeout(5000)
                else:
                    response = await page.goto(
                        url, 
                        wait_until=wait_strategy["wait_until"] if wait_strategy["wait_until"] != "custom" else "domcontentloaded",
                        timeout=wait_strategy["timeout"]
                    )
                
                # Check if page loaded successfully
                if response and response.status >= 400:
                    print(f"HTTP {response.status} error")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(5)
                        continue
                
                # Wait for JavaScript to render
                await self._wait_for_javascript(page)
                
                return
                
            except PlaywrightTimeout:
                if attempt < self.max_retries - 1:
                    print(f"Timeout on attempt {attempt + 1}, retrying...")
                    await asyncio.sleep(5)
                else:
                    print("Navigation failed after all retries")
                    raise
    
    async def _wait_for_javascript(self, page: Page) -> None:
        """Wait for JavaScript to render content."""
        try:
            # Wait for common loading indicators to disappear
            loading_selectors = [
                "[class*='loading']", "[class*='spinner']", 
                "[class*='loader']", ".loading", ".spinner"
            ]
            
            for selector in loading_selectors:
                try:
                    await page.wait_for_selector(selector, state="hidden", timeout=5000)
                except:
                    pass
            
            # Wait a bit for any animations
            await page.wait_for_timeout(1000)
            
        except Exception as e:
            print(f"Error waiting for JavaScript: {e}")
    
    async def _wait_for_content(self, page: Page, archive_pattern=None) -> None:
        """Wait for content to be ready."""
        if archive_pattern and archive_pattern.wait_selectors:
            for selector in archive_pattern.wait_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=10000, state="visible")
                    print(f"Content loaded: {selector}")
                    return
                except:
                    continue
        
        # Generic wait
        await page.wait_for_timeout(2000)
    
    async def _extract_page_data(self, page: Page, strategy: ScrapingStrategy, 
                                 archive_pattern=None) -> List[Dict[str, Any]]:
        """Extract data with enhanced selectors."""
        data = []
        
        # Try container-based extraction first
        if strategy.container_selector and strategy.item_selector:
            containers = await page.query_selector_all(strategy.container_selector)
            print(f"Found {len(containers)} containers with selector: {strategy.container_selector}")
            
            for container in containers:
                items = await container.query_selector_all(strategy.item_selector)
                print(f"Found {len(items)} items in container")
                
                for i, item in enumerate(items):
                    if i == 0:  # Debug first item
                        print(f"Field mappings: {strategy.field_mapping.mappings}")
                    item_data = await self._extract_item_data(
                        item, strategy.field_mapping.mappings, archive_pattern
                    )
                    if item_data and any(v for v in item_data.values()):
                        data.append(item_data)
                    elif i < 3:  # Debug why items are filtered out
                        print(f"Item {i} filtered out: {item_data}")
        
        # If no container strategy, try direct item selection
        if not data and archive_pattern:
            for item_hint in archive_pattern.item_hints:
                items = await page.query_selector_all(item_hint)
                if items:
                    print(f"Found {len(items)} items with hint: {item_hint}")
                    for item in items:
                        item_data = await self._extract_item_data(
                            item, strategy.field_mapping.mappings, archive_pattern
                        )
                        if item_data and any(v for v in item_data.values()):
                            data.append(item_data)
                    if data:
                        break
        
        # Last resort - try to find any repeating structures
        if not data:
            possible_items = await self._find_repeating_structures(page)
            for item in possible_items[:20]:  # Limit to prevent too much processing
                item_data = await self._extract_generic_data(item)
                if item_data and len(item_data) > 2:
                    data.append(item_data)
        
        return data
    
    async def _extract_item_data(self, element, field_mapping: Dict[str, str], 
                                 archive_pattern=None) -> Dict[str, Any]:
        """Extract data from a single item."""
        data = {}
        
        # Special handling for ArchNet
        if archive_pattern and archive_pattern.name == "ArchNet":
            # For ArchNet, we need to extract from their React data
            try:
                # Get page HTML
                html = await element.evaluate('el => el.ownerDocument.documentElement.outerHTML')
                soup = BeautifulSoup(html, 'html.parser')
                
                # Try to find data in parent or nearby elements
                parent = await element.evaluate('el => el.parentElement ? el.parentElement.outerHTML : null')
                if parent:
                    parent_soup = BeautifulSoup(parent, 'html.parser')
                    
                    # Extract from card structure
                    title_elem = parent_soup.select_one('.header, h3, a')
                    if title_elem:
                        data['Title'] = title_elem.get_text(strip=True)
                    
                    location_elem = parent_soup.select_one('.meta, .description')
                    if location_elem:
                        data['Orig. Location'] = location_elem.get_text(strip=True)
                    
                    # Extract link for ID
                    link = parent_soup.select_one('a[href*="/sites/"]')
                    if link:
                        href = link.get('href', '')
                        id_match = re.search(r'/sites/(\d+)', href)
                        if id_match:
                            data['Inventory #'] = id_match.group(1)
                    
                    data['Collection'] = 'ArchNet'
                    
                    # Get image
                    img = parent_soup.select_one('img')
                    if img:
                        data['image_url'] = img.get('src', '')
                    
                    return data if data.get('Title') else {}
                    
            except Exception as e:
                print(f"Error extracting ArchNet data: {e}")
                
        # Special handling for Machiel Kiel archive
        elif archive_pattern and archive_pattern.name == "Machiel Kiel Archive":
            title = await self._extract_title(element)
            if title:
                parsed = self._parse_kiel_title(title)
                data['Title'] = parsed.get('title', '')
                data['Orig. Location'] = parsed.get('location', '')
                data['Inventory #'] = parsed.get('inventory_num', '')
                data['Date photograph taken'] = parsed.get('date', '')
                data['Notes'] = parsed.get('description', '')
                data['Collection'] = 'Machiel Kiel Archive'
                
                # Get image URL
                link = await element.query_selector("a[href*='.jpg']")
                if link:
                    data['image_url'] = await link.get_attribute("href")
                
                return data
        
        # Handle label-value mappings
        if any(selector.startswith("_label_value:") for selector in field_mapping.values()):
            label_value_data = await self._extract_label_value_data(element)
            
            # Also extract standalone fields
            title = await self._extract_title(element)
            if title:
                label_value_data["title"] = title
            
            image = await self._extract_image(element)
            if image:
                label_value_data["image_url"] = image
            
            link = await self._extract_link(element)
            if link:
                label_value_data["detail_url"] = link
            
            # Map to schema fields
            for field_name, selector in field_mapping.items():
                if selector.startswith("_label_value:"):
                    web_field = selector.replace("_label_value:", "")
                    data[field_name] = label_value_data.get(web_field)
                else:
                    data[field_name] = None
        
        else:
            # Regular selector-based extraction
            for field_name, selector in field_mapping.items():
                try:
                    value = await self._extract_field_value(element, selector)
                    data[field_name] = value
                except:
                    data[field_name] = None
        
        return data
    
    async def _extract_label_value_data(self, element) -> Dict[str, str]:
        """Extract all label-value pairs from an element."""
        data = {}
        
        # Try different patterns
        patterns = [
            (".field", ".label", ".value"),
            (".metadata-item", ".metadata-label", ".metadata-value"),
            ("[class*='field']", "[class*='label']", "[class*='value']"),
            ("dt", "dt", "dd"),
            (".property", ".property-label", ".property-value")
        ]
        
        for field_sel, label_sel, value_sel in patterns:
            fields = await element.query_selector_all(field_sel)
            if fields:
                for field in fields:
                    try:
                        if field_sel == "dt":
                            label_elem = field
                            value_elem = await field.evaluate_handle("el => el.nextElementSibling")
                            if value_elem:
                                tag = await value_elem.evaluate("el => el.tagName")
                                if tag.lower() == "dd":
                                    label = await label_elem.inner_text()
                                    value = await value_elem.inner_text()
                                    key = self._normalize_label(label)
                                    data[key] = value.strip()
                        else:
                            label_elem = await field.query_selector(label_sel)
                            value_elem = await field.query_selector(value_sel)
                            if label_elem and value_elem:
                                label = await label_elem.inner_text()
                                value = await value_elem.inner_text()
                                key = self._normalize_label(label)
                                data[key] = value.strip()
                    except:
                        continue
                        
                if data:  # Found some data with this pattern
                    break
        
        return data
    
    async def _extract_title(self, element) -> Optional[str]:
        """Extract title from various possible locations."""
        title_selectors = [
            "h1", "h2", "h3", "h4", 
            ".title", "[class*='title']",
            "a:first-child", ".name", "[class*='name']"
        ]
        
        for selector in title_selectors:
            elem = await element.query_selector(selector)
            if elem:
                text = await elem.inner_text()
                if text and text.strip():
                    return text.strip()
        
        # Try to get from first link
        link = await element.query_selector("a")
        if link:
            text = await link.inner_text()
            if text and text.strip() and len(text.strip()) > 5:
                return text.strip()
            
            # Try link title attribute
            title_attr = await link.get_attribute("title")
            if title_attr and title_attr.strip():
                return title_attr.strip()
        
        # Last resort - get text content of the element itself
        try:
            text = await element.inner_text()
            if text and text.strip() and len(text.strip()) > 5:
                return text.strip()
        except:
            pass
        
        return None
    
    async def _extract_image(self, element) -> Optional[str]:
        """Extract image URL."""
        img = await element.query_selector("img")
        if img:
            src = await img.get_attribute("src") or await img.get_attribute("data-src")
            if src and not src.startswith('http'):
                # For relative URLs, we'll need to handle them later
                return src
            return src
        return None
    
    async def _extract_link(self, element) -> Optional[str]:
        """Extract detail/item link."""
        link = await element.query_selector("a[href]")
        if link:
            href = await link.get_attribute("href")
            if href and not href.startswith('#'):
                return href
        return None
    
    async def _extract_field_value(self, element, selector: str) -> Optional[str]:
        """Extract value using a selector."""
        elem = await element.query_selector(selector)
        if elem:
            # Check if it's an image
            tag = await elem.evaluate("el => el.tagName.toLowerCase()")
            if tag == "img":
                return await elem.get_attribute("src") or await elem.get_attribute("data-src")
            elif tag == "a":
                return await elem.get_attribute("href")
            else:
                text = await elem.inner_text()
                return text.strip() if text else None
        return None
    
    async def _extract_generic_data(self, element) -> Dict[str, Any]:
        """Extract generic data when no specific mapping is available."""
        data = {}
        
        # Extract text content
        text = await element.inner_text()
        if text and text.strip():
            data["text"] = text.strip()[:500]  # Limit length
        
        # Extract title
        title = await self._extract_title(element)
        if title:
            data["title"] = title
        
        # Extract image
        image = await self._extract_image(element)
        if image:
            data["image_url"] = image
        
        # Extract link
        link = await self._extract_link(element)
        if link:
            data["url"] = link
        
        # Extract any dates
        date_pattern = r'\b\d{4}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        if text:
            dates = re.findall(date_pattern, text)
            if dates:
                data["date"] = dates[0]
        
        return data
    
    async def _find_repeating_structures(self, page: Page) -> List:
        """Find repeating structures on the page."""
        selectors = [
            "[class*='item']", "[class*='result']", "[class*='card']",
            "[class*='entry']", "[class*='record']", "[class*='photo']",
            "article", "li", ".item", ".result"
        ]
        
        for selector in selectors:
            elements = await page.query_selector_all(selector)
            if len(elements) >= 3:
                return elements
        
        return []
    
    async def _navigate_to_next(self, page: Page, nav_strategy: NavigationStrategy, 
                                archive_pattern=None) -> bool:
        """Navigate to next page with enhanced handling."""
        if nav_strategy.method == "click_next":
            # Try next button selectors
            next_selectors = nav_strategy.selectors.get("next", [])
            if isinstance(next_selectors, str):
                next_selectors = [next_selectors]
            
            # Add common next selectors
            next_selectors.extend([
                "a:has-text('Next')", "a:has-text('>')",
                ".next", "[class*='next']", "a[rel='next']",
                "button:has-text('Next')", "[aria-label*='Next']"
            ])
            
            current_url = page.url
            
            for selector in next_selectors:
                try:
                    next_elem = await page.query_selector(selector)
                    if next_elem:
                        # Check if it's disabled
                        is_disabled = await next_elem.evaluate("el => el.disabled || el.classList.contains('disabled')")
                        if is_disabled:
                            continue
                        
                        # Take screenshot before navigation
                        await self._take_screenshot(page, "before_next")
                        
                        # Click and wait for navigation
                        await next_elem.click()
                        await page.wait_for_load_state("domcontentloaded", timeout=30000)
                        await self._wait_for_javascript(page)
                        
                        # Check if URL changed or content updated
                        new_url = page.url
                        if new_url != current_url:
                            print(f"Navigated to: {new_url}")
                            return True
                        else:
                            # URL didn't change, check if content updated
                            await asyncio.sleep(2)
                            return True
                            
                except Exception as e:
                    print(f"Error clicking next with {selector}: {e}")
                    continue
        
        elif nav_strategy.method == "pagination":
            # Handle numbered pagination
            current_page = nav_strategy.parameters.get("current_page", 1)
            next_page = current_page + 1
            
            # Try URL parameter approach
            current_url = page.url
            if "page=" in current_url:
                new_url = re.sub(r'page=\d+', f'page={next_page}', current_url)
            elif "?" in current_url:
                new_url = f"{current_url}&page={next_page}"
            else:
                new_url = f"{current_url}?page={next_page}"
            
            await page.goto(new_url, wait_until="domcontentloaded")
            nav_strategy.parameters["current_page"] = next_page
            return True
        
        elif nav_strategy.method == "scroll":
            # Handle infinite scroll
            return await self._handle_infinite_scroll(page)
        
        return False
    
    async def _handle_infinite_scroll(self, page: Page) -> bool:
        """Handle infinite scroll pagination."""
        # Get current scroll position
        prev_height = await page.evaluate("document.body.scrollHeight")
        
        # Scroll to bottom
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        
        # Wait for new content
        await page.wait_for_timeout(3000)
        
        # Check if new content loaded
        new_height = await page.evaluate("document.body.scrollHeight")
        
        return new_height > prev_height
    
    async def _try_export(self, page: Page, archive_pattern) -> Optional[List[Dict[str, Any]]]:
        """Try to use export functionality if available."""
        if not archive_pattern.export_selector:
            return None
        
        try:
            export_elem = await page.query_selector(archive_pattern.export_selector)
            if export_elem:
                # This would need implementation based on specific export formats
                print("Export functionality detected but not implemented")
                pass
        except:
            pass
        
        return None
    
    async def _try_scroll_loading(self, page: Page) -> None:
        """Try scrolling to trigger lazy loading."""
        await page.evaluate("window.scrollTo(0, window.innerHeight)")
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)
    
    async def _should_continue(self, data: List, page_count: int, max_pages: int) -> bool:
        """Determine if scraping should continue."""
        # Stop if we've reached max pages
        if page_count >= max_pages:
            return False
        
        # Stop if we haven't found any data after 3 pages
        if page_count >= 3 and len(data) == 0:
            print("No data found after 3 pages, stopping")
            return False
        
        return True
    
    async def _take_screenshot(self, page: Page, label: str, force: bool = False) -> None:
        """Take screenshot for debugging."""
        try:
            if force or self.screenshot_count < 10:  # Limit screenshots
                filename = f"screenshot_{self.screenshot_count:03d}_{label}.png"
                await page.screenshot(path=filename)
                print(f"Screenshot saved: {filename}")
                self.screenshot_count += 1
        except:
            pass
    
    def _normalize_label(self, label: str) -> str:
        """Normalize a label to a field key."""
        label = label.strip().rstrip(':').lower()
        label = re.sub(r'\s+', '_', label)
        label = re.sub(r'[^\w_]', '', label)
        
        # Keep # for inventory
        if 'inventory' in label and '#' in label:
            label = label.replace('_', '_#')
        
        return label
    
    def _parse_kiel_title(self, title: str) -> Dict[str, str]:
        """Parse Machiel Kiel archive title format."""
        data = {}
        
        # Remove .jpg extension
        title = title.replace('.jpg', '').replace('.JPG', '')
        
        # Extract inventory number and year from brackets [IV-121153, 1971]
        import re
        bracket_match = re.search(r'\[([^,\]]+),?\s*(\d{4})?\]', title)
        if bracket_match:
            data['inventory_num'] = bracket_match.group(1).strip()
            if bracket_match.group(2):
                data['date'] = bracket_match.group(2)
            # Remove the bracket part from title
            title = title[:bracket_match.start()].strip()
        
        # Split by comma to get location and description
        parts = title.split(',', 1)
        if len(parts) >= 1:
            data['location'] = parts[0].strip()
        if len(parts) >= 2:
            data['description'] = parts[1].strip()
        
        # Full title without .jpg
        data['title'] = title
        
        return data
    
    async def _handle_pre_navigation(self, page: Page, archive_pattern: 'ArchivePattern') -> None:
        """Handle pre-navigation steps required before data appears."""
        for step in archive_pattern.pre_navigation_steps:
            action = step.get("action")
            
            if action == "select":
                selector = step.get("selector")
                value = step.get("value")
                wait_after = step.get("wait_after", 1000)
                
                print(f"Selecting {value} in {selector}")
                try:
                    # Find the select element
                    select_elem = await page.query_selector(selector)
                    if select_elem:
                        # Select the option
                        await page.select_option(selector, value)
                        print(f"Selected {value}")
                        
                        # Wait for any dynamic updates
                        await page.wait_for_timeout(wait_after)
                    else:
                        print(f"Select element not found: {selector}")
                except Exception as e:
                    print(f"Error in select action: {e}")
            
            elif action == "click":
                selector = step.get("selector")
                wait_after = step.get("wait_after", 1000)
                
                print(f"Clicking {selector}")
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        await elem.click()
                        await page.wait_for_timeout(wait_after)
                    else:
                        print(f"Element not found: {selector}")
                except Exception as e:
                    print(f"Error in click action: {e}")
            
            elif action == "wait":
                timeout = step.get("timeout", 1000)
                await page.wait_for_timeout(timeout)
        
        # Wait for content to stabilize after pre-navigation
        await page.wait_for_load_state("domcontentloaded")
        await self._wait_for_javascript(page)