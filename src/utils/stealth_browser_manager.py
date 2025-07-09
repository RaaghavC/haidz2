"""
Stealth Browser Manager with anti-detection capabilities.
Uses playwright-stealth to make browser automation undetectable.
"""

import asyncio
import logging
import random
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth
from fake_useragent import UserAgent
import aiohttp
from aiohttp_socks import ProxyConnector

# Set up logging
logger = logging.getLogger(__name__)


class StealthBrowserManager:
    """
    Browser manager with stealth capabilities to avoid detection.
    """
    
    def __init__(
        self,
        headless: bool = True,
        proxy_config: Optional[Dict[str, Any]] = None,
        use_stealth: bool = True,
        viewport_size: Optional[Dict[str, int]] = None
    ):
        """
        Initialize the stealth browser manager.
        
        Args:
            headless: Whether to run browser in headless mode
            proxy_config: Proxy configuration (url, username, password)
            use_stealth: Whether to apply stealth patches
            viewport_size: Custom viewport size
        """
        self.headless = headless
        self.proxy_config = proxy_config
        self.use_stealth = use_stealth
        self.viewport_size = viewport_size or {"width": 1920, "height": 1080}
        
        # Initialize user agent generator with fallback
        try:
            self.ua = UserAgent()
        except:
            # Fallback if UserAgent fails
            self.ua = None
        
        # Browser instances
        self.playwright = None
        self.browser = None
        self.context = None
        
        logger.info("Initialized StealthBrowserManager")
    
    def _get_random_user_agent(self) -> str:
        """Get a random realistic user agent"""
        # Prefer Chrome user agents as they're most common
        if self.ua:
            try:
                return self.ua.chrome
            except:
                pass
        
        # Fallback to a known good user agent
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def _get_browser_args(self) -> List[str]:
        """Get browser launch arguments for stealth"""
        args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-accelerated-2d-canvas',
            '--disable-gpu',
            '--window-size=1920,1080',
            '--start-maximized',
            '--disable-infobars',
            '--disable-notifications',
            '--disable-popup-blocking',
            '--ignore-certificate-errors',
            '--allow-running-insecure-content'
        ]
        
        # Add proxy if configured
        if self.proxy_config and 'server' in self.proxy_config:
            args.append(f'--proxy-server={self.proxy_config["server"]}')
        
        return args
    
    async def start(self):
        """Start the browser with stealth configuration"""
        logger.info("Starting stealth browser...")
        
        self.playwright = await async_playwright().start()
        
        # Browser launch options
        launch_options = {
            "headless": self.headless,
            "args": self._get_browser_args(),
        }
        
        # Add proxy configuration if provided
        if self.proxy_config:
            launch_options["proxy"] = {
                "server": self.proxy_config.get("server"),
                "username": self.proxy_config.get("username"),
                "password": self.proxy_config.get("password")
            }
        
        # Launch Chromium (most compatible with stealth)
        self.browser = await self.playwright.chromium.launch(**launch_options)
        
        # Create context with stealth options
        context_options = {
            "viewport": self.viewport_size,
            "user_agent": self._get_random_user_agent(),
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["geolocation", "notifications"],
            "geolocation": {"latitude": 40.7128, "longitude": -74.0060},  # New York
            "color_scheme": "light",
            "device_scale_factor": 1,
            "is_mobile": False,
            "has_touch": False,
            "extra_http_headers": {
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
        }
        
        self.context = await self.browser.new_context(**context_options)
        
        # Apply additional context-level stealth
        await self.context.add_init_script("""
            // Override navigator properties
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override chrome runtime
            window.chrome = {
                runtime: {}
            };
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    }
                ]
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)
        
        logger.info("Stealth browser started successfully")
    
    async def stop(self):
        """Stop the browser and clean up resources"""
        logger.info("Stopping browser...")
        
        if self.context:
            await self.context.close()
        
        if self.browser:
            await self.browser.close()
        
        if self.playwright:
            await self.playwright.stop()
        
        logger.info("Browser stopped")
    
    @asynccontextmanager
    async def new_page(self) -> Page:
        """
        Create a new page with stealth applied.
        
        Yields:
            Page instance with stealth patches
        """
        if not self.context:
            await self.start()
        
        page = await self.context.new_page()
        
        # Apply stealth patches
        if self.use_stealth:
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
        
        # Additional page-level stealth configurations
        await page.evaluate("""
            // Remove Playwright fingerprints
            delete window.__playwright;
            delete window.__pw_manual;
            delete window.playwright;
        """)
        
        # Random delays to appear more human
        page.set_default_timeout(30000)
        page.set_default_navigation_timeout(30000)
        
        try:
            yield page
        finally:
            await page.close()
    
    async def get_page(self, url: str, wait_for: str = "domcontentloaded") -> str:
        """
        Navigate to a URL and return the page HTML.
        
        Args:
            url: URL to navigate to
            wait_for: Wait condition ('domcontentloaded', 'networkidle', 'load')
            
        Returns:
            Page HTML content
        """
        async with self.new_page() as page:
            # Add random delay before navigation
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # Navigate with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await page.goto(url, wait_until=wait_for)
                    
                    if response and response.status >= 400:
                        logger.warning(f"HTTP {response.status} for {url}")
                    
                    # Random delay after page load
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                    
                    # Scroll to trigger lazy loading
                    await self._human_like_scroll(page)
                    
                    # Get the HTML content
                    html = await page.content()
                    
                    return html
                    
                except Exception as e:
                    logger.error(f"Error loading {url} (attempt {attempt + 1}): {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(random.uniform(2.0, 5.0))
                    else:
                        raise
    
    async def _human_like_scroll(self, page: Page):
        """
        Perform human-like scrolling to trigger lazy loading.
        
        Args:
            page: Page instance to scroll
        """
        # Get page dimensions
        dimensions = await page.evaluate("""
            () => {
                return {
                    width: document.documentElement.clientWidth,
                    height: document.documentElement.clientHeight,
                    scrollHeight: document.documentElement.scrollHeight
                }
            }
        """)
        
        current_position = 0
        scroll_height = dimensions['scrollHeight']
        viewport_height = dimensions['height']
        
        # Scroll in chunks with random delays
        while current_position < scroll_height:
            # Random scroll distance (between 100-500 pixels)
            scroll_distance = random.randint(100, 500)
            current_position += scroll_distance
            
            # Ensure we don't scroll past the end
            current_position = min(current_position, scroll_height)
            
            # Smooth scroll
            await page.evaluate(f"window.scrollTo({{top: {current_position}, behavior: 'smooth'}})")
            
            # Random delay between scrolls (simulate reading)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Sometimes scroll back up a bit (natural behavior)
            if random.random() < 0.1:  # 10% chance
                back_scroll = random.randint(50, 200)
                current_position -= back_scroll
                await page.evaluate(f"window.scrollTo({{top: {current_position}, behavior: 'smooth'}})")
                await asyncio.sleep(random.uniform(0.3, 0.8))
        
        # Scroll back to top sometimes
        if random.random() < 0.3:  # 30% chance
            await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
    
    async def click_element(self, page: Page, selector: str):
        """
        Click an element with human-like behavior.
        
        Args:
            page: Page instance
            selector: CSS selector of element to click
        """
        try:
            # Wait for element to be visible
            await page.wait_for_selector(selector, state="visible")
            
            # Get element position
            element = await page.query_selector(selector)
            if not element:
                raise ValueError(f"Element not found: {selector}")
            
            # Hover with random offset
            box = await element.bounding_box()
            if box:
                x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
                y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
                
                # Move mouse to element with random speed
                await page.mouse.move(x, y, steps=random.randint(5, 15))
                
                # Random delay before click
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
                # Click
                await page.mouse.click(x, y)
            else:
                # Fallback to regular click
                await element.click()
                
        except Exception as e:
            logger.error(f"Error clicking element {selector}: {str(e)}")
            raise
    
    async def fill_input(self, page: Page, selector: str, text: str):
        """
        Fill an input field with human-like typing.
        
        Args:
            page: Page instance
            selector: CSS selector of input field
            text: Text to type
        """
        try:
            # Click the input field first
            await self.click_element(page, selector)
            
            # Clear existing content
            await page.fill(selector, "")
            
            # Type with random delays between characters
            for char in text:
                await page.keyboard.type(char)
                # Random delay between 50-200ms
                await asyncio.sleep(random.uniform(0.05, 0.2))
            
        except Exception as e:
            logger.error(f"Error filling input {selector}: {str(e)}")
            raise
    
    async def wait_for_navigation(self, page: Page):
        """
        Wait for navigation with random delay.
        
        Args:
            page: Page instance
        """
        await page.wait_for_load_state("networkidle")
        # Additional random delay
        await asyncio.sleep(random.uniform(1.0, 3.0))