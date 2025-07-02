"""
Manar al-Athar extraction strategy
"""

import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from src.strategies.base_strategy import BaseExtractionStrategy
from src.models.schemas import ArchiveRecord

logger = logging.getLogger(__name__)


class ManarStrategy(BaseExtractionStrategy):
    """
    Specialized strategy for Manar al-Athar archive
    Uses targeted selectors based on their site structure
    """
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.manar-al-athar.ox.ac.uk"
        
    async def extract(
        self, 
        url: str, 
        search_query: str = "",
        max_results: int = 500
    ) -> List[ArchiveRecord]:
        """
        Extract data from Manar al-Athar
        """
        logger.info(f"🏛️ Manar Strategy: Extracting from {url}")
        if search_query:
            logger.info(f"🔍 Search query: '{search_query}'")
        
        all_records = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Navigate to search page if search query provided
                if search_query:
                    search_url = f"{self.base_url}/pages/advanced_search.php"
                    await page.goto(search_url, wait_until='networkidle')
                    
                    # Fill search form
                    await page.fill('input[name="search"]', search_query)
                    await page.click('input[type="submit"]')
                    await page.wait_for_load_state('networkidle')
                else:
                    await page.goto(url, wait_until='networkidle')
                
                # Extract images from result grid
                processed_pages = 0
                
                while len(all_records) < max_results and processed_pages < 10:
                    # Wait for content
                    await page.wait_for_selector('.ResourcePanel, .ResultPanel, [class*="result"]', timeout=10000)
                    
                    # Extract items
                    items = await page.query_selector_all('.ResourcePanel, .ResultPanel, [class*="result"]')
                    
                    for item in items:
                        if len(all_records) >= max_results:
                            break
                            
                        try:
                            # Extract metadata from item
                            title = await item.query_selector('.Title, .title, h3')
                            title_text = await title.inner_text() if title else ''
                            
                            # Get image URL
                            img = await item.query_selector('img')
                            img_url = await img.get_attribute('src') if img else ''
                            if img_url and not img_url.startswith('http'):
                                img_url = f"{self.base_url}/{img_url.lstrip('/')}"
                            
                            # Get metadata text
                            metadata = await item.query_selector('.ResourcePanelInfo, .metadata, .info')
                            metadata_text = await metadata.inner_text() if metadata else ''
                            
                            # Parse metadata
                            record = {
                                'title': title_text,
                                'name': title_text,
                                'content_url': img_url,
                                'thumbnail_url': img_url,
                                'source': 'Manar al-Athar',
                                'type': 'Image',
                                'description': metadata_text
                            }
                            
                            # Extract specific fields from metadata
                            lines = metadata_text.split('\n') if metadata_text else []
                            for line in lines:
                                if ':' in line:
                                    key, value = line.split(':', 1)
                                    key = key.strip().lower()
                                    value = value.strip()
                                    
                                    if 'location' in key:
                                        record['place_name'] = value
                                    elif 'date' in key:
                                        record['date_photo_taken'] = value
                                    elif 'photographer' in key:
                                        record['photographer'] = value
                                    elif 'collection' in key:
                                        record['collection'] = value
                                        
                            all_records.append(record)
                            
                        except Exception as e:
                            logger.warning(f"Failed to extract item: {e}")
                            continue
                    
                    # Check for next page
                    next_button = await page.query_selector('a[title="Next page"], .next-page, a:has-text("Next")')
                    if next_button and await next_button.is_visible():
                        await next_button.click()
                        await page.wait_for_load_state('networkidle')
                        processed_pages += 1
                    else:
                        break
                        
            except Exception as e:
                logger.error(f"Error during Manar extraction: {e}")
            finally:
                await browser.close()
        
        # Filter by search query if needed
        if search_query and all_records:
            all_records = self.filter_by_search_query(all_records, search_query)
        
        logger.info(f"✅ Extracted {len(all_records)} records from Manar al-Athar")
        
        # Convert to ArchiveRecord objects
        return self.convert_to_archive_records(all_records)