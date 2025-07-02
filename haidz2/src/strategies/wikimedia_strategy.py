"""
Wikimedia Commons extraction strategy using MediaWiki API
"""

import asyncio
import logging
from typing import List, Dict, Any
import requests
from urllib.parse import urlencode, urlparse

from src.strategies.base_strategy import BaseExtractionStrategy
from src.models.schemas import ArchiveRecord

logger = logging.getLogger(__name__)


class WikimediaStrategy(BaseExtractionStrategy):
    """
    Specialized strategy for Wikimedia Commons using MediaWiki API
    """
    
    def __init__(self):
        super().__init__()
        self.api_endpoint = "https://commons.wikimedia.org/w/api.php"
        
    async def search_images(
        self, 
        search_query: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search for images using MediaWiki API"""
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': f'{search_query} filemime:image',
            'srnamespace': '6',  # File namespace
            'srlimit': min(limit, 500),
            'srprop': 'snippet|titlesnippet|size|wordcount|timestamp'
        }
        
        try:
            response = requests.get(self.api_endpoint, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('query', {}).get('search', [])
            else:
                logger.error(f"MediaWiki search failed: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error searching MediaWiki: {e}")
            return []
    
    async def get_image_info(
        self, 
        page_ids: List[str]
    ) -> Dict[str, Any]:
        """Get detailed info for images"""
        if not page_ids:
            return {}
            
        params = {
            'action': 'query',
            'format': 'json',
            'pageids': '|'.join(page_ids[:50]),  # Max 50 at a time
            'prop': 'imageinfo|categories',
            'iiprop': 'timestamp|user|url|size|metadata|commonmetadata|extmetadata'
        }
        
        try:
            response = requests.get(self.api_endpoint, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('query', {}).get('pages', {})
            else:
                logger.error(f"MediaWiki imageinfo failed: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Error getting image info: {e}")
            return {}
    
    def parse_wikimedia_image(
        self, 
        page_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Wikimedia image data into our format"""
        imageinfo = page_data.get('imageinfo', [{}])[0]
        extmetadata = imageinfo.get('extmetadata', {})
        
        # Extract metadata
        title = page_data.get('title', '').replace('File:', '')
        
        # Get description from various sources
        description = ''
        if 'ImageDescription' in extmetadata:
            description = extmetadata['ImageDescription'].get('value', '')
        elif 'ObjectName' in extmetadata:
            description = extmetadata['ObjectName'].get('value', '')
            
        # Get location
        location = ''
        if 'GPSLatitude' in extmetadata and 'GPSLongitude' in extmetadata:
            lat = extmetadata['GPSLatitude'].get('value', '')
            lon = extmetadata['GPSLongitude'].get('value', '')
            location = f"{lat}, {lon}"
        elif 'LocationDest' in extmetadata:
            location = extmetadata['LocationDest'].get('value', '')
            
        # Get date
        date_taken = extmetadata.get('DateTimeOriginal', {}).get('value', '')
        if not date_taken:
            date_taken = extmetadata.get('DateTime', {}).get('value', '')
            
        return {
            'title': title,
            'name': title,
            'description': description,
            'photographer': extmetadata.get('Artist', {}).get('value', imageinfo.get('user', '')),
            'copyright': extmetadata.get('Copyright', {}).get('value', ''),
            'license': extmetadata.get('License', {}).get('value', ''),
            'date_photo_taken': date_taken,
            'place_name': location,
            'content_url': imageinfo.get('url', ''),
            'thumbnail_url': imageinfo.get('thumburl', ''),
            'source': 'Wikimedia Commons',
            'type': 'Image',
            'record_id': str(page_data.get('pageid', ''))
        }
    
    async def extract(
        self, 
        url: str, 
        search_query: str = "",
        max_results: int = 500
    ) -> List[ArchiveRecord]:
        """
        Extract data from Wikimedia Commons using MediaWiki API
        """
        logger.info(f"🌐 Wikimedia Strategy: Extracting from {url}")
        
        # Default search for architecture if no query provided
        if not search_query:
            # Extract category from URL if possible
            if 'Category:' in url:
                search_query = url.split('Category:')[-1].replace('_', ' ')
            else:
                search_query = 'architecture'
                
        logger.info(f"🔍 Search query: '{search_query}'")
        
        all_records = []
        
        # Search for images
        search_results = await self.search_images(search_query, max_results)
        
        if not search_results:
            logger.warning("No search results found")
            return []
            
        # Get detailed info for found images
        page_ids = [str(result['pageid']) for result in search_results]
        
        # Process in batches of 50
        for i in range(0, len(page_ids), 50):
            batch_ids = page_ids[i:i+50]
            pages_info = await self.get_image_info(batch_ids)
            
            for page_id, page_data in pages_info.items():
                if 'imageinfo' in page_data:
                    parsed = self.parse_wikimedia_image(page_data)
                    all_records.append(parsed)
                    
                    if len(all_records) >= max_results:
                        break
                        
            if len(all_records) >= max_results:
                break
                
            # Rate limiting
            await asyncio.sleep(0.5)
        
        logger.info(f"✅ Extracted {len(all_records)} records from Wikimedia Commons")
        
        # Convert to ArchiveRecord objects
        return self.convert_to_archive_records(all_records)