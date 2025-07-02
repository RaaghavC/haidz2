"""
ArchNet-specific extraction strategy using Algolia API
"""

import asyncio
import logging
from typing import List, Dict, Any
import aiohttp
import ssl
import requests

from src.strategies.base_strategy import BaseExtractionStrategy
from src.models.schemas import ArchiveRecord

logger = logging.getLogger(__name__)


class ArchNetStrategy(BaseExtractionStrategy):
    """
    Specialized strategy for ArchNet using their Algolia search API
    """
    
    def __init__(self):
        super().__init__()
        self.algolia_app_id = "ZPU971PZKC"
        self.algolia_search_key = "8a6ae24beaa5f55705dd42b122554f0b"
        self.algolia_index = "production"
        self.base_url = "https://zpu971pzkc-dsn.algolia.net/1/indexes/production/query"
        self.iiif_base = "https://archnet-3-prod-iiif-cloud-c0fe51f0b9ac.herokuapp.com"
        
    def get_algolia_headers(self) -> Dict[str, str]:
        """Get headers for Algolia API requests"""
        return {
            'X-Algolia-Application-Id': self.algolia_app_id,
            'X-Algolia-API-Key': self.algolia_search_key,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def search_algolia(
        self, 
        query: str = "", 
        filters: str = "", 
        hits_per_page: int = 100, 
        page: int = 0
    ) -> Dict[str, Any]:
        """Search Algolia index for records"""
        search_params = {
            "query": query,
            "filters": filters,
            "hitsPerPage": hits_per_page,
            "page": page,
            "facets": ["*"],
            "attributesToRetrieve": ["*"]
        }
        
        # Use requests with SSL bypass for simplicity
        try:
            response = requests.post(
                self.base_url,
                headers=self.get_algolia_headers(),
                json=search_params,
                verify=False  # Disable SSL verification
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Algolia search failed: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Error searching Algolia: {e}")
            return {}
    
    def parse_algolia_hit(self, hit: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Algolia hit into our format"""
        # Extract location info
        country_info = hit.get('country', {})
        country = country_info.get('name', '') if isinstance(country_info, dict) else str(country_info)
        place_name = hit.get('place_name', '')
        location = f"{place_name}, {country}".strip(', ')
        
        # Parse record
        return {
            'record_id': hit.get('record_id', hit.get('objectID', '')),
            'name': hit.get('name', hit.get('title', '')),
            'title': hit.get('name', hit.get('title', '')),
            'place_name': location,
            'country': country,
            'year': hit.get('year'),
            'media_type': hit.get('media_type', {}).get('name', '') if isinstance(hit.get('media_type'), dict) else '',
            'photographer': hit.get('photographer', ''),
            'copyright': hit.get('copyright', ''),
            'caption': hit.get('caption', ''),
            'description': hit.get('description', hit.get('caption', '')),
            'contributor': hit.get('contributor', ''),
            'source': hit.get('source', ''),
            'content_url': hit.get('content_url', ''),
            'iiif_url': hit.get('content_iiif_url', ''),
            'thumbnail_url': hit.get('content_thumbnail_url', ''),
            'type': hit.get('type', 'Image')
        }
    
    async def extract(
        self, 
        url: str, 
        search_query: str = "",
        max_results: int = 500
    ) -> List[ArchiveRecord]:
        """
        Extract data from ArchNet using Algolia API
        """
        logger.info(f"🏛️ ArchNet Strategy: Extracting from {url}")
        if search_query:
            logger.info(f"🔍 Search query: '{search_query}'")
        
        all_records = []
        page = 0
        
        # Use search query if provided, otherwise get all images
        algolia_query = search_query
        filters = 'type:"Image"' if not search_query else ''
        
        while len(all_records) < max_results:
            logger.info(f"Fetching page {page + 1}...")
            
            # search_algolia is sync, so just call it directly
            result = self.search_algolia(
                algolia_query,
                filters,
                100,
                page
            )
            
            if not result or 'hits' not in result:
                break
                
            hits = result['hits']
            if not hits:
                break
                
            # Parse and filter hits
            for hit in hits:
                if len(all_records) >= max_results:
                    break
                    
                parsed = self.parse_algolia_hit(hit)
                
                # Apply additional filtering if search query was used with filters
                if search_query and filters:
                    # Check if search terms appear in the parsed data
                    record_text = ' '.join(str(v).lower() for v in parsed.values() if v)
                    if not all(term.lower() in record_text for term in search_query.split()):
                        continue
                
                all_records.append(parsed)
            
            # Check if we've reached the end
            if len(hits) < 100:
                break
                
            page += 1
            
            # Rate limiting
            await asyncio.sleep(0.5)
        
        logger.info(f"✅ Extracted {len(all_records)} records from ArchNet")
        
        # Convert to ArchiveRecord objects
        return self.convert_to_archive_records(all_records)