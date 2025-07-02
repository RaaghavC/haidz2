"""
Hybrid executor that uses direct HTTP requests when possible, falling back to browser automation.
"""

import asyncio
from typing import List, Dict, Any, Optional
from src.models.strategies import ScrapingStrategy
from src.modules.archnet_extractor import ArchNetExtractor
from src.modules.manar_extractor import ManarExtractor
from src.modules.enhanced_executor import EnhancedExecutor
from src.strategies.archive_patterns import get_pattern_for_url


class HybridExecutor:
    """Executes scraping using the most efficient method for each archive."""
    
    def __init__(self):
        self.enhanced_executor = EnhancedExecutor()
        self.direct_extractors = {
            'ArchNet': ArchNetExtractor(),
            'Manar al-Athar': ManarExtractor()
        }
    
    async def execute_strategy(self, strategy: ScrapingStrategy, page: Optional[Any] = None) -> List[Dict[str, Any]]:
        """Execute scraping strategy using the best method for the archive."""
        archive_pattern = get_pattern_for_url(strategy.url)
        
        # Check if we have a direct extractor for this archive
        if archive_pattern and archive_pattern.name in self.direct_extractors:
            print(f"Using direct HTTP extraction for {archive_pattern.name}")
            return await self._execute_direct(strategy, archive_pattern)
        else:
            # Fall back to browser-based extraction
            print("Using browser-based extraction")
            return await self.enhanced_executor.execute_strategy(strategy, page)
    
    async def _execute_direct(self, strategy: ScrapingStrategy, archive_pattern) -> List[Dict[str, Any]]:
        """Execute using direct HTTP extraction."""
        extractor = self.direct_extractors[archive_pattern.name]
        all_data = []
        
        # Extract based on navigation strategy
        max_pages = strategy.navigation_strategy.parameters.get('max_pages', 1)
        
        for page_num in range(1, max_pages + 1):
            print(f"\nExtracting page {page_num}")
            
            if archive_pattern.name == 'ArchNet':
                # Use the ArchNet extractor
                sites = extractor.extract_sites_list(page_num)
                
                # Convert to standard format
                for site in sites:
                    data = {
                        'Title': site.get('title', ''),
                        'Orig. Location': site.get('location', ''),
                        'Collection': site.get('collection', ''),
                        'Inventory #': site.get('inventory_num', ''),
                        'Typ': site.get('type', ''),
                        'Notes': site.get('description', ''),
                        'image_url': site.get('image_url', '')
                    }
                    all_data.append(data)
                
                print(f"Extracted {len(sites)} items from page {page_num}")
                
                # Stop if no more data
                if not sites:
                    break
            
            elif archive_pattern.name == 'Manar al-Athar':
                # Use the Manar extractor
                photos = extractor.extract_search_results(page_num)
                
                # Convert to standard format
                for photo in photos:
                    data = {
                        'Title': photo.get('title', ''),
                        'Orig. Location': photo.get('location', ''),
                        'Collection': photo.get('collection', ''),
                        'Inventory #': photo.get('inventory_num', ''),
                        'Typ': photo.get('type', ''),
                        'Notes': photo.get('notes', ''),
                        'image_url': photo.get('image_url', '')
                    }
                    all_data.append(data)
                
                print(f"Extracted {len(photos)} items from page {page_num}")
                
                # Stop if no more data
                if not photos:
                    break
        
        return all_data