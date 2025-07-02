#!/usr/bin/env python3
"""
ArchNet Algolia-based comprehensive metadata extractor
Uses discovered Algolia search API to extract ALL metadata fields
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import aiohttp
import requests
import ssl
from playwright.async_api import async_playwright
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ArchNetRecord:
    """Comprehensive ArchNet record structure"""
    record_id: str
    name: str
    place_name: Optional[str]
    country: Optional[str]
    year: Optional[int]
    media_type: Optional[str]
    photographer: Optional[str]
    copyright: Optional[str]
    caption: Optional[str]
    contributor: Optional[str]
    source: Optional[str]
    content_url: Optional[str]
    iiif_url: Optional[str]
    manifest_url: Optional[str]
    thumbnail_url: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    raw_data: Dict[str, Any]

class ArchNetAlgoliaExtractor:
    """
    Comprehensive ArchNet extractor using Algolia search API
    Extracts ALL metadata fields using discovered API endpoints
    """
    
    def __init__(self):
        self.algolia_app_id = "ZPU971PZKC"
        self.algolia_search_key = "8a6ae24beaa5f55705dd42b122554f0b"
        self.algolia_index = "production"
        self.base_url = "https://zpu971pzkc-dsn.algolia.net/1/indexes/production/query"
        self.iiif_base = "https://archnet-3-prod-iiif-cloud-c0fe51f0b9ac.herokuapp.com"
        self.session = None
        self.extracted_records = []
        
    async def __aenter__(self):
        # Create SSL context that doesn't verify certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        self.session = aiohttp.ClientSession(connector=connector)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def get_algolia_headers(self) -> Dict[str, str]:
        """Get headers for Algolia API requests"""
        return {
            'X-Algolia-Application-Id': self.algolia_app_id,
            'X-Algolia-API-Key': self.algolia_search_key,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    async def search_algolia(self, query: str = "", filters: str = "", hits_per_page: int = 100, page: int = 0) -> Dict[str, Any]:
        """Search Algolia index for records"""
        search_params = {
            "query": query,
            "filters": filters,
            "hitsPerPage": hits_per_page,
            "page": page,
            "facets": ["*"],
            "attributesToRetrieve": ["*"]
        }
        
        # Try aiohttp first
        try:
            async with self.session.post(
                self.base_url,
                headers=self.get_algolia_headers(),
                json=search_params
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Algolia response: {len(result.get('hits', []))} hits, {result.get('nbHits', 0)} total")
                    return result
                else:
                    logger.error(f"Algolia search failed: {response.status}")
                    response_text = await response.text()
                    logger.error(f"Response: {response_text[:500]}")
        except Exception as e:
            logger.error(f"Error with aiohttp search: {e}")
        
        # Fallback to requests library
        try:
            logger.info("Falling back to requests library")
            response = requests.post(
                self.base_url,
                headers=self.get_algolia_headers(),
                json=search_params,
                verify=False  # Disable SSL verification
            )
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Requests response: {len(result.get('hits', []))} hits, {result.get('nbHits', 0)} total")
                return result
            else:
                logger.error(f"Requests fallback failed: {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")
        except Exception as e:
            logger.error(f"Error with requests fallback: {e}")
        
        return {}
    
    async def get_iiif_manifest(self, resource_id: str) -> Dict[str, Any]:
        """Get IIIF manifest for detailed metadata"""
        manifest_url = f"{self.iiif_base}/public/resources/{resource_id}/manifest"
        
        # Try aiohttp first
        try:
            async with self.session.get(manifest_url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"IIIF manifest not found for {resource_id} (aiohttp)")
        except Exception as e:
            logger.error(f"Error fetching IIIF manifest with aiohttp: {e}")
        
        # Fallback to requests
        try:
            response = requests.get(manifest_url, verify=False)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"IIIF manifest not found for {resource_id} (requests)")
        except Exception as e:
            logger.error(f"Error fetching IIIF manifest with requests: {e}")
        
        return {}
    
    def extract_resource_id_from_url(self, url: str) -> Optional[str]:
        """Extract resource ID from IIIF URLs"""
        if not url:
            return None
        # Extract UUID from URL like: https://archnet-3-prod-iiif-cloud-c0fe51f0b9ac.herokuapp.com/public/resources/f80e6234-b461-4af3-b67f-34d50e987400/content
        try:
            parts = url.split('/resources/')
            if len(parts) > 1:
                return parts[1].split('/')[0]
        except:
            pass
        return None
    
    def parse_record(self, hit: Dict[str, Any]) -> ArchNetRecord:
        """Parse Algolia hit into structured record"""
        try:
            # Extract basic info
            record_id = hit.get('record_id', hit.get('objectID', ''))
            name = hit.get('name', hit.get('title', ''))
            place_name = hit.get('place_name', '')
            
            # Extract country info
            country_info = hit.get('country', {})
            country = country_info.get('name', '') if isinstance(country_info, dict) else str(country_info)
            
            # Extract location coordinates
            latitude = None
            longitude = None
            if isinstance(country_info, dict):
                try:
                    latitude = float(country_info.get('latitude', 0))
                    longitude = float(country_info.get('longitude', 0))
                except (ValueError, TypeError):
                    pass
            
            # Extract media info
            year = hit.get('year')
            media_type_info = hit.get('media_type', {})
            media_type = media_type_info.get('name', '') if isinstance(media_type_info, dict) else str(media_type_info)
            
            # Extract photographer/copyright info
            photographer = hit.get('photographer', '')
            copyright_info = hit.get('copyright', '')
            caption = hit.get('caption', '')
            contributor = hit.get('contributor', '')
            source = hit.get('source', '')
            
            # Extract IIIF URLs
            content_url = hit.get('content_url', '')
            iiif_url = hit.get('content_iiif_url', '')
            manifest_url = hit.get('manifest_url', '')
            thumbnail_url = hit.get('content_thumbnail_url', '')
            
            return ArchNetRecord(
                record_id=record_id,
                name=name,
                place_name=place_name,
                country=country,
                year=year,
                media_type=media_type,
                photographer=photographer,
                copyright=copyright_info,
                caption=caption,
                contributor=contributor,
                source=source,
                content_url=content_url,
                iiif_url=iiif_url,
                manifest_url=manifest_url,
                thumbnail_url=thumbnail_url,
                latitude=latitude,
                longitude=longitude,
                raw_data=hit
            )
        except Exception as e:
            logger.error(f"Error parsing record: {e}")
            return None
    
    async def search_and_extract_images(self, max_records: int = 500) -> List[ArchNetRecord]:
        """Search for images and extract comprehensive metadata"""
        logger.info("Starting comprehensive ArchNet extraction using Algolia API")
        
        # First try without filters to see if we get any data
        logger.info("Testing Algolia connection without filters...")
        test_result = await self.search_algolia(query="", filters="", hits_per_page=10, page=0)
        if test_result and 'hits' in test_result:
            logger.info(f"Test query successful: {len(test_result['hits'])} hits")
            if test_result['hits']:
                logger.info(f"Sample hit keys: {list(test_result['hits'][0].keys())}")
                # Check what types are available
                sample_hit = test_result['hits'][0]
                logger.info(f"Sample type: {sample_hit.get('type', 'No type field')}")
                if 'primary_image' in sample_hit:
                    logger.info(f"Has primary_image: {bool(sample_hit['primary_image'])}")
        else:
            logger.error("Test query failed - no data returned")
            return []
        
        # Try different filter approaches for images
        filter_options = [
            'type:"Image"',  # Try Image type
            'type:"image"',  # Try lowercase
            'primary_image:*',  # Records with primary_image field
            ''  # No filter - get everything
        ]
        
        best_filter = ""
        max_hits = 0
        
        for filter_test in filter_options:
            logger.info(f"Testing filter: '{filter_test}'")
            test_result = await self.search_algolia(query="", filters=filter_test, hits_per_page=10, page=0)
            if test_result and 'nbHits' in test_result:
                hits_count = test_result['nbHits']
                logger.info(f"Filter '{filter_test}' returned {hits_count} total hits")
                if hits_count > max_hits:
                    max_hits = hits_count
                    best_filter = filter_test
        
        logger.info(f"Using best filter: '{best_filter}' with {max_hits} total hits")
        image_filters = best_filter
        page = 0
        all_records = []
        
        while len(all_records) < max_records:
            logger.info(f"Fetching page {page + 1}...")
            
            search_result = await self.search_algolia(
                query="",
                filters=image_filters,
                hits_per_page=100,
                page=page
            )
            
            if not search_result or 'hits' not in search_result:
                logger.warning("No more results found")
                break
            
            hits = search_result['hits']
            if not hits:
                logger.info("No more hits available")
                break
            
            # Parse each hit into structured record
            for hit in hits:
                record = self.parse_record(hit)
                if record:
                    all_records.append(record)
                    
                    # Get additional IIIF metadata if available
                    if record.iiif_url:
                        resource_id = self.extract_resource_id_from_url(record.iiif_url)
                        if resource_id:
                            iiif_manifest = await self.get_iiif_manifest(resource_id)
                            if iiif_manifest:
                                # Enhance record with IIIF metadata
                                record.raw_data['iiif_manifest'] = iiif_manifest
            
            logger.info(f"Extracted {len(all_records)} records so far")
            
            # Check if we've reached the end
            if len(hits) < 100:
                break
            
            page += 1
            
            # Rate limiting
            await asyncio.sleep(1)
        
        logger.info(f"Total records extracted: {len(all_records)}")
        self.extracted_records = all_records
        return all_records
    
    async def save_results(self, filename: str = None):
        """Save extracted records to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"archnet_comprehensive_extraction_{timestamp}.json"
        
        # Convert records to dictionaries for JSON serialization
        data = []
        for record in self.extracted_records:
            record_dict = {
                'record_id': record.record_id,
                'name': record.name,
                'place_name': record.place_name,
                'country': record.country,
                'year': record.year,
                'media_type': record.media_type,
                'photographer': record.photographer,
                'copyright': record.copyright,
                'caption': record.caption,
                'contributor': record.contributor,
                'source': record.source,
                'content_url': record.content_url,
                'iiif_url': record.iiif_url,
                'manifest_url': record.manifest_url,
                'thumbnail_url': record.thumbnail_url,
                'latitude': record.latitude,
                'longitude': record.longitude,
                'raw_data': record.raw_data
            }
            data.append(record_dict)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Results saved to {filename}")
        return filename
    
    def print_sample_records(self, count: int = 5):
        """Print sample records for verification"""
        logger.info(f"Sample of {min(count, len(self.extracted_records))} records:")
        
        for i, record in enumerate(self.extracted_records[:count]):
            print(f"\n--- Record {i+1} ---")
            print(f"ID: {record.record_id}")
            print(f"Name: {record.name}")
            print(f"Location: {record.place_name}, {record.country}")
            print(f"Year: {record.year}")
            print(f"Media Type: {record.media_type}")
            print(f"Photographer: {record.photographer}")
            print(f"Copyright: {record.copyright}")
            print(f"Caption: {record.caption[:100]}..." if record.caption else "Caption: None")
            print(f"IIIF URL: {record.iiif_url}")

async def main():
    """Main execution function"""
    async with ArchNetAlgoliaExtractor() as extractor:
        # Extract comprehensive metadata
        records = await extractor.search_and_extract_images(max_records=500)
        
        # Save results
        filename = await extractor.save_results()
        
        # Print sample records
        extractor.print_sample_records(10)
        
        print(f"\nExtraction complete!")
        print(f"Total records: {len(records)}")
        print(f"Results saved to: {filename}")

if __name__ == "__main__":
    asyncio.run(main())