"""Browser manager for Playwright lifecycle management."""

from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class BrowserManager:
    """Manages Playwright browser instances and contexts."""
    
    def __init__(self):
        """Initialize the browser manager."""
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.default_options = {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-features=site-per-process",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins",
                "--disable-site-isolation-trials",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",
                "--window-size=1920,1080",
                "--start-maximized",
                "--disable-features=IsolateOrigins,site-per-process",
                "--flag-switches-begin",
                "--flag-switches-end",
                "--disable-features=TranslateUI",
                "--disable-features=BlinkGenPropertyTrees",
                "--lang=en-US,en"
            ]
        }
    
    async def start(self, options: Optional[Dict[str, Any]] = None) -> None:
        """
        Start the browser instance.
        
        Args:
            options: Browser launch options
        """
        if self.browser:
            return
        
        self.playwright = await async_playwright().start()
        launch_options = {**self.default_options, **(options or {})}
        
        # Use Chromium for best compatibility
        self.browser = await self.playwright.chromium.launch(**launch_options)
    
    async def stop(self) -> None:
        """Stop the browser instance."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
    
    @asynccontextmanager
    async def create_context(self, options: Optional[Dict[str, Any]] = None):
        """
        Create a new browser context.
        
        Args:
            options: Context options (viewport, user agent, etc.)
            
        Yields:
            BrowserContext instance
        """
        if not self.browser:
            await self.start()
        
        default_context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "accept_downloads": False,
            "bypass_csp": True,
            "ignore_https_errors": True,
            "extra_http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }
        }
        
        context_options = {**default_context_options, **(options or {})}
        context = await self.browser.new_context(**context_options)
        
        try:
            yield context
        finally:
            await context.close()
    
    @asynccontextmanager
    async def create_page(self, context_options: Optional[Dict[str, Any]] = None):
        """
        Create a new page in a new context.
        
        Args:
            context_options: Options for the browser context
            
        Yields:
            Page instance
        """
        async with self.create_context(context_options) as context:
            page = await context.new_page()
            
            # Set up common event handlers
            page.on("dialog", lambda dialog: dialog.accept())
            
            # Set default timeout
            page.set_default_timeout(120000)  # 120 seconds
            
            # Add stealth scripts
            await page.add_init_script("""
                // Overwrite the `navigator.webdriver` property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Mock permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            try:
                yield page
            finally:
                await page.close()