"""
Autonomous Navigator for intelligent site exploration.
This module enables the scraper to start from any landing page and 
autonomously navigate to find actual image records.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re

from playwright.async_api import Page
from openai import OpenAI
from anthropic import Anthropic

# Set up logging
logger = logging.getLogger(__name__)


class AutonomousNavigator:
    """
    Navigates through archive sites autonomously to find image records.
    Uses AI to understand site structure and make navigation decisions.
    """
    
    def __init__(
        self,
        api_key: str,
        provider: str = "openai",
        max_depth: int = 5
    ):
        """
        Initialize the autonomous navigator.
        
        Args:
            api_key: API key for LLM
            provider: LLM provider
            max_depth: Maximum navigation depth
        """
        self.provider = provider
        self.max_depth = max_depth
        
        if provider == "openai":
            self.client = OpenAI(api_key=api_key)
            self.model = "gpt-4-turbo-preview"
        else:
            self.client = Anthropic(api_key=api_key)
            self.model = "claude-3-opus-20240229"
        
        # Track visited URLs to avoid loops
        self.visited_urls: Set[str] = set()
        
        # Common patterns for finding images in archives
        self.image_patterns = [
            # Link text patterns
            r'view\s+image|image\s+details?|view\s+details?|full\s+record',
            r'photograph|photo|picture|artwork|painting|drawing',
            r'view\s+of|interior|exterior|facade',  # Common architectural terms
            
            # URL patterns
            r'/items?/|/images?/|/photos?/|/artworks?/|/objects?/',
            r'/detail/|/view/|/record/|/entry/',
            r'media_content_id=',  # ArchNet specific
            r'/sites/\d+\?media',  # ArchNet pattern
            r'/authorities/\d+\?media',  # ArchNet pattern
            
            # Class/ID patterns
            r'item-link|image-link|result-item|search-result',
            r'collection-item|archive-item|record-link'
        ]
        
        self.collection_patterns = [
            r'collections?|archives?|galleries?|exhibitions?',
            r'browse|search|explore|discover',
            r'results?|listings?|catalog'
        ]
        
        logger.info(f"Initialized AutonomousNavigator with {provider}")
    
    async def find_path_to_images(
        self,
        page: Page,
        start_url: str,
        search_term: str
    ) -> List[str]:
        """
        Find paths from landing page to actual image records.
        
        Args:
            page: Playwright page instance
            start_url: Starting URL
            search_term: Search term (e.g., "Antakya")
            
        Returns:
            List of URLs to individual image pages
        """
        logger.info(f"Starting autonomous navigation from {start_url}")
        logger.info(f"Looking for: {search_term}")
        
        # Reset visited URLs for new session
        self.visited_urls.clear()
        
        # Start navigation
        image_urls = await self._explore_site(
            page=page,
            current_url=start_url,
            search_term=search_term,
            depth=0
        )
        
        logger.info(f"Found {len(image_urls)} potential image URLs")
        return list(image_urls)
    
    async def _explore_site(
        self,
        page: Page,
        current_url: str,
        search_term: str,
        depth: int
    ) -> Set[str]:
        """
        Recursively explore site to find image pages.
        
        Args:
            page: Playwright page instance
            current_url: Current URL
            search_term: Search term
            depth: Current depth
            
        Returns:
            Set of image URLs found
        """
        if depth > self.max_depth or current_url in self.visited_urls:
            return set()
        
        self.visited_urls.add(current_url)
        image_urls = set()
        
        try:
            # Navigate to current URL if needed
            if page.url != current_url:
                await page.goto(current_url, wait_until="networkidle")
                await page.wait_for_timeout(2000)  # Let dynamic content load
            
            # Get page content
            content = await page.content()
            
            # First, try to use search if available
            search_performed = await self._try_search(page, search_term)
            if search_performed:
                await page.wait_for_timeout(3000)  # Wait for results
                content = await page.content()
            
            # Analyze page with AI
            navigation_plan = await self._analyze_page_with_ai(
                content,
                current_url,
                search_term
            )
            
            # Check if current page has image links
            current_image_urls = self._extract_image_urls(content, current_url)
            
            # Special handling for ArchNet and similar sites
            # If URL contains media_content_id, this IS an image page
            if 'media_content_id=' in current_url:
                logger.info(f"Found image page: {current_url}")
                image_urls.add(current_url)
                return image_urls
            
            image_urls.update(current_image_urls)
            
            # If we found images, we might be done at this level
            if current_image_urls:
                logger.info(f"Found {len(current_image_urls)} image URLs at depth {depth}")
                
                # Return early if we have enough
                if len(image_urls) >= 10:
                    return image_urls
            
            # If no images found, follow navigation plan
            elif depth < self.max_depth and navigation_plan['should_explore']:
                # Follow recommended links
                for link_info in navigation_plan['recommended_links'][:5]:
                    url = link_info['url']
                    if url not in self.visited_urls:
                        logger.info(f"Following link: {link_info['text']} -> {url}")
                        
                        # Navigate and explore
                        sub_urls = await self._explore_site(
                            page, url, search_term, depth + 1
                        )
                        image_urls.update(sub_urls)
                        
                        # If we found images, we might not need to explore more
                        if len(image_urls) >= 10:
                            break
            
        except Exception as e:
            logger.error(f"Error exploring {current_url}: {str(e)}")
        
        return image_urls
    
    async def _try_search(self, page: Page, search_term: str) -> bool:
        """
        Try to find and use search functionality.
        
        Args:
            page: Playwright page
            search_term: Term to search for
            
        Returns:
            True if search was performed
        """
        try:
            # Common search input selectors
            search_selectors = [
                'input[type="search"]',
                'input[name="q"]',
                'input[name="query"]',
                'input[name="search"]',
                'input[name="keyword"]',
                'input[placeholder*="search" i]',
                'input[placeholder*="ara" i]',  # Turkish
                'input[class*="search" i]',
                '#search',
                '.search-input'
            ]
            
            for selector in search_selectors:
                try:
                    search_input = await page.query_selector(selector)
                    if search_input and await search_input.is_visible():
                        logger.info(f"Found search input: {selector}")
                        
                        # Clear and type search term
                        await search_input.click()
                        await search_input.fill("")
                        await search_input.type(search_term, delay=100)
                        
                        # Submit search
                        await page.keyboard.press("Enter")
                        
                        # Wait for navigation or results
                        try:
                            await page.wait_for_navigation(timeout=5000)
                        except:
                            # Sometimes results load without navigation
                            await page.wait_for_timeout(2000)
                        
                        return True
                except:
                    continue
            
            # Try to find search button and form
            search_form = await page.query_selector('form[action*="search"]')
            if search_form:
                search_input = await search_form.query_selector('input[type="text"]')
                if search_input:
                    await search_input.fill(search_term)
                    
                    # Find submit button
                    submit_button = await search_form.query_selector('button[type="submit"], input[type="submit"]')
                    if submit_button:
                        await submit_button.click()
                        await page.wait_for_timeout(3000)
                        return True
            
        except Exception as e:
            logger.debug(f"Search attempt failed: {str(e)}")
        
        return False
    
    async def _analyze_page_with_ai(
        self,
        html_content: str,
        current_url: str,
        search_term: str
    ) -> Dict[str, Any]:
        """
        Use AI to understand page structure and navigation options.
        
        Args:
            html_content: Page HTML
            current_url: Current URL
            search_term: What we're looking for
            
        Returns:
            Navigation analysis and recommendations
        """
        # Extract key page elements
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Get page title and main headings
        title = soup.find('title')
        title_text = title.get_text(strip=True) if title else "No title"
        
        headings = []
        for h in soup.find_all(['h1', 'h2', 'h3'])[:10]:
            headings.append(h.get_text(strip=True))
        
        # Get navigation links
        links = []
        for a in soup.find_all('a', href=True)[:50]:
            link_text = a.get_text(strip=True)
            if link_text and len(link_text) > 2:
                links.append({
                    'text': link_text[:100],
                    'href': a['href'],
                    'classes': ' '.join(a.get('class', []))
                })
        
        # Create prompt for AI
        prompt = f"""Analyze this archive/museum website page and determine how to navigate to find individual image/photo records about "{search_term}".

Current URL: {current_url}
Page Title: {title_text}

Main Headings:
{chr(10).join(f"- {h}" for h in headings[:10])}

Available Links (first 50):
{chr(10).join(f"- {link['text']} [{link['href']}]" for link in links[:20])}

Questions to answer:
1. What type of page is this? (homepage, search results, collection page, item detail, etc.)
2. Are there individual image/photo records on this page? 
3. Which links should I follow to find individual photos/images of {search_term}?
4. Is there a search function visible? How do I use it?

Provide response as JSON with:
- page_type: Type of current page
- has_individual_images: true/false
- has_search: true/false  
- should_explore: true/false
- recommended_links: Array of top 5 links to follow, each with url, text, and reason
- strategy: Brief description of navigation strategy
"""

        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert at navigating digital archives and museum websites."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                
                import json
                result = json.loads(response.choices[0].message.content)
                
            else:  # anthropic
                response = self.client.messages.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=1000
                )
                
                import json
                result = json.loads(response.content[0].text)
            
            # Process recommended links to full URLs
            base_url = f"{urlparse(current_url).scheme}://{urlparse(current_url).netloc}"
            for link in result.get('recommended_links', []):
                if 'url' in link:
                    link['url'] = urljoin(current_url, link['url'])
            
            return result
            
        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            return {
                'page_type': 'unknown',
                'has_individual_images': False,
                'should_explore': True,
                'recommended_links': []
            }
    
    def _extract_image_urls(self, html_content: str, base_url: str) -> Set[str]:
        """
        Extract URLs that likely lead to individual image records.
        
        Args:
            html_content: Page HTML
            base_url: Base URL for relative links
            
        Returns:
            Set of potential image URLs
        """
        soup = BeautifulSoup(html_content, 'lxml')
        image_urls = set()
        
        # Look for links that match image patterns
        for pattern in self.image_patterns:
            # Check link text
            for a in soup.find_all('a', string=re.compile(pattern, re.I)):
                if a.get('href'):
                    url = urljoin(base_url, a['href'])
                    image_urls.add(url)
            
            # Check link URLs
            for a in soup.find_all('a', href=re.compile(pattern, re.I)):
                url = urljoin(base_url, a['href'])
                image_urls.add(url)
            
            # Check classes
            for a in soup.find_all('a', class_=re.compile(pattern, re.I)):
                if a.get('href'):
                    url = urljoin(base_url, a['href'])
                    image_urls.add(url)
        
        # Also look for figure/article elements with links
        for container in soup.find_all(['figure', 'article', 'div']):
            # Check if it looks like an item container
            if container.find('img') and container.find('a'):
                for a in container.find_all('a'):
                    if a.get('href'):
                        url = urljoin(base_url, a['href'])
                        if any(pattern in url.lower() for pattern in ['/item', '/image', '/photo', '/detail']):
                            image_urls.add(url)
        
        return image_urls
    
    async def navigate_to_next_page(self, page: Page) -> bool:
        """
        Try to navigate to the next page of results.
        
        Args:
            page: Playwright page
            
        Returns:
            True if navigation successful
        """
        try:
            # Common next page selectors
            next_selectors = [
                'a[aria-label*="next" i]',
                'a[title*="next" i]',
                'button[aria-label*="next" i]',
                'a.next',
                'a.pagination-next',
                'a[rel="next"]',
                'a:has-text("Next")',
                'a:has-text("»")',
                'a:has-text("→")',
                '.pagination a:last-child',
                'a[href*="page="]:last-of-type'
            ]
            
            for selector in next_selectors:
                try:
                    next_elem = await page.query_selector(selector)
                    if next_elem and await next_elem.is_visible():
                        # Check if it's not disabled
                        disabled = await next_elem.get_attribute('disabled')
                        if not disabled:
                            await next_elem.click()
                            await page.wait_for_timeout(2000)
                            return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error navigating to next page: {str(e)}")
            return False