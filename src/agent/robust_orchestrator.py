"""
Robust Orchestrator for AI-powered scraping with enhanced capabilities.
Manages the high-level scraping process with Plan-Execute-Verify loop.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from pathlib import Path

from src.modules.intelligent_extractor import IntelligentExtractor, MuseumItemSchema
from src.modules.resource_verifier import ResourceVerifier
from src.utils.stealth_browser_manager import StealthBrowserManager
from src.modules.robust_data_handler import DataHandler
from src.utils.monitoring import ProgressMonitor
from src.utils.rate_limiter import RateLimiter, ARCHIVE_RATE_LIMITS
from src.utils.proxy_manager import ProxyManager
from src.agent.autonomous_navigator import AutonomousNavigator

# Set up logging
logger = logging.getLogger(__name__)


class ScrapingResult:
    """Result of a scraping operation."""
    def __init__(
        self,
        success: bool,
        items_scraped: int,
        items: List[Any],
        errors: List[str],
        metadata: Dict[str, Any]
    ):
        self.success = success
        self.items_scraped = items_scraped
        self.items = items
        self.errors = errors
        self.metadata = metadata


class RobustOrchestrator:
    """
    Enhanced orchestrator that coordinates all components for robust scraping.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = "openai",
        headless: bool = True,
        proxy_config: Optional[Dict[str, Any]] = None,
        output_format: str = "csv"
    ):
        """
        Initialize the robust orchestrator.
        
        Args:
            api_key: API key for LLM provider
            provider: LLM provider ('openai' or 'anthropic')
            headless: Whether to run browser in headless mode
            proxy_config: Proxy configuration
            output_format: Output format for results
        """
        # Initialize core components
        self.extractor = IntelligentExtractor(api_key=api_key, provider=provider)
        self.verifier = ResourceVerifier(api_key=api_key, provider=provider)
        self.browser_manager = StealthBrowserManager(
            headless=headless,
            proxy_config=proxy_config,
            use_stealth=True
        )
        self.data_handler = DataHandler(output_format=output_format)
        
        # Initialize autonomous navigator for intelligent site exploration
        self.navigator = AutonomousNavigator(
            api_key=api_key,
            provider=provider,
            max_depth=5
        )
        
        # Initialize monitoring and rate limiting
        self.monitor = ProgressMonitor(update_interval=5.0)
        self.rate_limiter = RateLimiter(domain_configs=ARCHIVE_RATE_LIMITS)
        
        # Initialize proxy manager if configured
        self.proxy_manager = None
        if proxy_config:
            self.proxy_manager = ProxyManager(proxy_list=[proxy_config])
        
        # Scraping state
        self.results = []
        self.failed_urls = []
        self.stats = {
            'total_pages_visited': 0,
            'total_items_found': 0,
            'total_items_extracted': 0,
            'total_items_verified': 0,
            'total_items_filtered': 0,
            'start_time': None,
            'end_time': None
        }
        
        logger.info("Initialized RobustOrchestrator")
    
    async def scrape(
        self,
        start_url: str,
        search_query: Optional[str] = None,
        max_results: int = 100,
        max_pages: int = 10
    ) -> ScrapingResult:
        """
        Main scraping method following Plan-Execute-Verify loop.
        
        Args:
            start_url: Starting URL for scraping
            search_query: Optional search query
            max_results: Maximum number of results to collect
            max_pages: Maximum number of pages to visit
            
        Returns:
            ScrapingResult with all extracted data
        """
        logger.info(f"Starting robust scraping: {start_url}")
        logger.info(f"Search query: {search_query}")
        logger.info(f"Max results: {max_results}, Max pages: {max_pages}")
        
        self.stats['start_time'] = datetime.now()
        self.monitor.start_session()
        
        try:
            # Start the browser
            await self.browser_manager.start()
            
            # PLAN: Use autonomous navigator to find actual image pages
            logger.info("Starting autonomous navigation to find image records...")
            
            async with self.browser_manager.new_page() as page:
                # Navigate to starting URL
                await page.goto(start_url, wait_until="networkidle")
                
                # Use autonomous navigator to find paths to actual images
                search_term = search_query or "Antakya"  # Default search if none provided
                image_urls = await self.navigator.find_path_to_images(
                    page=page,
                    start_url=start_url,
                    search_term=search_term
                )
                
                # If navigator found image URLs, extract from them
                if image_urls:
                    logger.info(f"Autonomous navigator found {len(image_urls)} potential image pages")
                    await self._extract_from_image_urls(image_urls[:max_results])
                else:
                    # Fallback to original approach if navigator fails
                    logger.warning("Autonomous navigation found no images, trying direct extraction")
                    if search_query:
                        await self._execute_search_scraping(start_url, search_query, max_results, max_pages)
                    else:
                        await self._execute_browse_scraping(start_url, max_results, max_pages)
            
            # VERIFY: Validate and filter results
            verified_results = await self._verify_results()
            
            # Create final result
            self.stats['end_time'] = datetime.now()
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            result = ScrapingResult(
                success=True,
                items_scraped=len(verified_results),
                items=verified_results,
                errors=[],
                metadata={
                    'stats': self.stats,
                    'duration_seconds': duration,
                    'failed_urls': self.failed_urls
                }
            )
            
            # Save results
            await self._save_results(verified_results)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in orchestrator: {str(e)}")
            return ScrapingResult(
                success=False,
                items_scraped=0,
                items=[],
                errors=[str(e)],
                metadata=self.stats
            )
        finally:
            # Clean up
            await self.browser_manager.stop()
    
    async def _plan_scraping_approach(self, url: str, search_query: Optional[str]) -> Dict[str, Any]:
        """
        Plan the scraping approach based on the target site and query.
        
        Args:
            url: Target URL
            search_query: Optional search query
            
        Returns:
            Scraping plan dictionary
        """
        # Analyze the site to determine best approach
        html = await self.browser_manager.get_page(url)
        
        plan = {
            'approach': 'search' if search_query else 'browse',
            'site_type': 'unknown',
            'has_search': False,
            'pagination_type': 'unknown',
            'item_selector': None
        }
        
        # Check for known site patterns
        if 'archnet.org' in url:
            plan['site_type'] = 'archnet'
            plan['has_search'] = True
            plan['item_selector'] = 'div.search-result-item'
        elif 'wikimedia.org' in url:
            plan['site_type'] = 'wikimedia'
            plan['has_search'] = True
            plan['item_selector'] = 'li.mw-search-result'
        elif 'manar-al-athar' in url:
            plan['site_type'] = 'manar'
            plan['has_search'] = True
            plan['item_selector'] = 'div.item-record'
        
        return plan
    
    async def _execute_search_scraping(
        self,
        start_url: str,
        search_query: str,
        max_results: int,
        max_pages: int
    ):
        """
        Execute search-based scraping.
        
        Args:
            start_url: Starting URL
            search_query: Search query
            max_results: Maximum results to collect
            max_pages: Maximum pages to visit
        """
        async with self.browser_manager.new_page() as page:
            # Navigate to the site
            await page.goto(start_url)
            await page.wait_for_load_state("networkidle")
            
            # Look for search input
            search_selectors = [
                'input[type="search"]',
                'input[name="q"]',
                'input[name="query"]',
                'input[name="search"]',
                'input[placeholder*="search" i]',
                'input[placeholder*="ara" i]'  # For Turkish "ara" (search)
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await page.query_selector(selector)
                    if search_input:
                        logger.info(f"Found search input: {selector}")
                        break
                except:
                    continue
            
            if not search_input:
                logger.warning("No search input found, falling back to browse mode")
                await self._execute_browse_scraping(start_url, max_results, max_pages)
                return
            
            # Perform search
            await self.browser_manager.fill_input(page, selector, search_query)
            await page.keyboard.press("Enter")
            await self.browser_manager.wait_for_navigation(page)
            
            # Extract results from search pages
            pages_visited = 0
            while pages_visited < max_pages and len(self.results) < max_results:
                pages_visited += 1
                self.stats['total_pages_visited'] += 1
                
                # Get page HTML
                html = await page.content()
                
                # Extract items from current page
                await self._extract_items_from_page(html, page.url)
                
                # Check for next page
                next_button = await self._find_next_button(page)
                if next_button and len(self.results) < max_results:
                    await self.browser_manager.click_element(page, next_button)
                    await self.browser_manager.wait_for_navigation(page)
                else:
                    break
    
    async def _execute_browse_scraping(
        self,
        start_url: str,
        max_results: int,
        max_pages: int
    ):
        """
        Execute browse-based scraping (no search).
        
        Args:
            start_url: Starting URL
            max_results: Maximum results to collect
            max_pages: Maximum pages to visit
        """
        visited_urls = set()
        urls_to_visit = [start_url]
        pages_visited = 0
        
        while urls_to_visit and pages_visited < max_pages and len(self.results) < max_results:
            url = urls_to_visit.pop(0)
            
            if url in visited_urls:
                continue
            
            visited_urls.add(url)
            pages_visited += 1
            self.stats['total_pages_visited'] += 1
            
            try:
                # Apply rate limiting
                start_time = datetime.now()
                await self.rate_limiter.acquire(url)
                
                # Get page HTML
                html = await self.browser_manager.get_page(url)
                
                # Record metrics
                response_time = (datetime.now() - start_time).total_seconds()
                self.monitor.record_page_visit(url, response_time)
                self.rate_limiter.report_success(url)
                
                # Check if this is an image page
                verification = await self.verifier.verify_resource_type(html, url)
                
                if verification['should_extract']:
                    # Extract data from this page
                    await self._extract_single_item(html, url)
                else:
                    # Look for links to potential image pages
                    async with self.browser_manager.new_page() as page:
                        await page.goto(url)
                        
                        # Find links that might lead to image pages
                        links = await page.query_selector_all('a[href*="image"], a[href*="photo"], a[href*="item"]')
                        
                        for link in links[:10]:  # Limit to 10 links per page
                            href = await link.get_attribute('href')
                            if href and href not in visited_urls:
                                # Make absolute URL
                                if not href.startswith('http'):
                                    href = page.url.split('?')[0].rstrip('/') + '/' + href.lstrip('/')
                                urls_to_visit.append(href)
                
            except Exception as e:
                logger.error(f"Error processing {url}: {str(e)}")
                self.failed_urls.append(url)
    
    async def _extract_items_from_page(self, html: str, page_url: str):
        """
        Extract multiple items from a search results page.
        
        Args:
            html: Page HTML
            page_url: Current page URL
        """
        try:
            # Try to find item containers
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            
            # Common item selectors for archives
            item_selectors = [
                'div.search-result',
                'div.item',
                'article.result',
                'li.result-item',
                'div.grid-item',
                'div.collection-item'
            ]
            
            items_found = False
            for selector in item_selectors:
                items = soup.select(selector)
                if items:
                    logger.info(f"Found {len(items)} items with selector: {selector}")
                    self.stats['total_items_found'] += len(items)
                    
                    for item in items:
                        if len(self.results) >= 100:  # Safety limit
                            break
                        
                        # Quick check if this looks like an image item
                        item_html = str(item)
                        if any(word in item_html.lower() for word in ['collection', 'authority', 'site']):
                            self.stats['total_items_filtered'] += 1
                            continue
                        
                        # Extract data from item
                        extraction_start = datetime.now()
                        extracted = await self.extractor.extract_from_html(item_html)
                        extraction_time = (datetime.now() - extraction_start).total_seconds()
                        
                        if extracted:
                            for result in extracted:
                                if result.typ == "Image":
                                    self.results.append(result)
                                    self.stats['total_items_extracted'] += 1
                                    self.monitor.record_item_extracted(result.dict(), extraction_time)
                    
                    items_found = True
                    break
            
            if not items_found:
                # Try to extract as a single item
                await self._extract_single_item(html, page_url)
                
        except Exception as e:
            logger.error(f"Error extracting items: {str(e)}")
    
    async def _extract_single_item(self, html: str, page_url: str):
        """
        Extract a single item from a page.
        
        Args:
            html: Page HTML
            page_url: Page URL
        """
        try:
            # Verify this is an image resource
            verification = await self.verifier.verify_resource_type(html, page_url)
            
            if not verification['should_extract']:
                logger.info(f"Skipping non-image resource: {verification['resource_type']}")
                self.stats['total_items_filtered'] += 1
                return
            
            # Extract data
            items = await self.extractor.extract_from_html(html)
            
            for item in items:
                if item.typ == "Image":
                    # Add page URL to item
                    if not item.image_quality:
                        item.image_quality = page_url
                    
                    self.results.append(item)
                    self.stats['total_items_extracted'] += 1
                    logger.info(f"Extracted image: {item.title}")
                    
        except Exception as e:
            logger.error(f"Error extracting single item: {str(e)}")
    
    async def _find_next_button(self, page) -> Optional[str]:
        """
        Find the next page button on the current page.
        
        Args:
            page: Playwright page instance
            
        Returns:
            CSS selector for next button or None
        """
        # Common next button patterns
        next_selectors = [
            'a[aria-label*="next" i]',
            'a[title*="next" i]',
            'button[aria-label*="next" i]',
            'a.next',
            'a.pagination-next',
            'a[rel="next"]',
            'a:has-text("Next")',
            'a:has-text("»")',
            'a:has-text("→")'
        ]
        
        for selector in next_selectors:
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    return selector
            except:
                continue
        
        return None
    
    async def _extract_from_image_urls(self, image_urls: List[str]):
        """
        Extract data from a list of image URLs found by the navigator.
        
        Args:
            image_urls: List of URLs to individual image pages
        """
        logger.info(f"Extracting data from {len(image_urls)} image pages")
        
        for url in image_urls:
            if url in self.failed_urls:
                continue
                
            try:
                # Apply rate limiting
                start_time = datetime.now()
                await self.rate_limiter.acquire(url)
                
                # Get page HTML
                html = await self.browser_manager.get_page(url)
                
                # Record metrics
                response_time = (datetime.now() - start_time).total_seconds()
                self.monitor.record_page_visit(url, response_time)
                self.rate_limiter.report_success(url)
                
                # Verify this is actually an image page
                verification = await self.verifier.verify_resource_type(html, url)
                
                if verification['should_extract']:
                    # Extract data
                    extraction_start = datetime.now()
                    items = await self.extractor.extract_from_html(html)
                    extraction_time = (datetime.now() - extraction_start).total_seconds()
                    
                    for item in items:
                        if item.typ == "Image":
                            # Add source URL
                            if not item.image_quality:
                                item.image_quality = url
                            
                            self.results.append(item)
                            self.stats['total_items_extracted'] += 1
                            self.monitor.record_item_extracted(item.dict(), extraction_time)
                            logger.info(f"Extracted: {item.title}")
                else:
                    logger.info(f"Skipping non-image resource at {url}")
                    self.stats['total_items_filtered'] += 1
                    
            except Exception as e:
                logger.error(f"Error extracting from {url}: {str(e)}")
                self.failed_urls.append(url)
                self.rate_limiter.report_error(url)
    
    async def _verify_results(self) -> List[MuseumItemSchema]:
        """
        Verify and filter results based on location and date criteria.
        
        Returns:
            List of verified results
        """
        verified = []
        
        for item in self.results:
            # Verify location (must be Antakya)
            location_check = self.verifier.verify_location(
                item.orig_location or item.notes or ""
            )
            
            if not location_check['is_antakya']:
                logger.info(f"Filtered out non-Antakya item: {item.title}")
                self.stats['total_items_filtered'] += 1
                continue
            
            # Verify date (must be pre-earthquake)
            date_text = (
                str(item.date_photograph_taken or "") + " " +
                str(item.notes or "")
            )
            date_check = self.verifier.verify_date(date_text)
            
            if not date_check['is_pre_earthquake']:
                logger.info(f"Filtered out post-earthquake item: {item.title}")
                self.stats['total_items_filtered'] += 1
                continue
            
            verified.append(item)
            self.stats['total_items_verified'] += 1
        
        logger.info(f"Verified {len(verified)} items out of {len(self.results)} total")
        return verified
    
    async def _save_results(self, results: List[MuseumItemSchema]):
        """
        Save results to file.
        
        Args:
            results: List of verified results
        """
        if not results:
            logger.warning("No results to save")
            return
        
        # Convert to dictionaries
        data = [item.dict() for item in results]
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Save to CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"robust_scrape_results_{timestamp}.csv"
        
        df.to_csv(f"csv/{filename}", index=False)
        logger.info(f"Saved {len(results)} results to csv/{filename}")