"""
API Detection Strategy - Intelligently detects and uses APIs
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import aiohttp
import ssl
import json
import re
from urllib.parse import urlparse

from src.strategies.base_strategy import BaseExtractionStrategy
from src.models.schemas import ArchiveRecord

logger = logging.getLogger(__name__)


class APIDetectionStrategy(BaseExtractionStrategy):
    """
    Intelligent strategy that detects APIs and data endpoints
    """
    
    def __init__(self):
        super().__init__()
        self.detected_api = None
        
    async def detect_api(self, url: str) -> Dict[str, Any]:
        """
        Detect API endpoints by analyzing the site
        """
        logger.info(f"🔍 Detecting APIs for {url}")
        
        api_info = {
            'has_api': False,
            'api_type': None,
            'endpoints': [],
            'auth_required': False
        }
        
        try:
            # Create SSL context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            async with aiohttp.ClientSession() as session:
                # Check common API endpoints
                domain = urlparse(url).netloc
                base_url = f"https://{domain}"
                
                # Common API patterns to check
                api_patterns = [
                    '/api/',
                    '/api/v1/',
                    '/api/v2/',
                    '/wp-json/',  # WordPress
                    '/rest/',
                    '/data/',
                    '/search/api/',
                    '/_api/',
                    '/services/',
                ]
                
                for pattern in api_patterns:
                    test_url = f"{base_url}{pattern}"
                    try:
                        async with session.get(test_url, ssl=ssl_context, timeout=5) as response:
                            if response.status == 200:
                                content_type = response.headers.get('Content-Type', '')
                                if 'json' in content_type:
                                    api_info['has_api'] = True
                                    api_info['endpoints'].append(test_url)
                                    
                                    # Try to identify API type
                                    content = await response.text()
                                    if 'swagger' in content.lower():
                                        api_info['api_type'] = 'swagger'
                                    elif 'graphql' in content.lower():
                                        api_info['api_type'] = 'graphql'
                                    elif 'rest' in test_url:
                                        api_info['api_type'] = 'rest'
                                        
                                    logger.info(f"✅ Found API endpoint: {test_url}")
                                    
                    except Exception:
                        continue
                
                # Check for exposed data files
                data_patterns = [
                    '/data.json',
                    '/api/data.json',
                    '/search/results.json',
                    '/collections.json',
                    '/items.json'
                ]
                
                for pattern in data_patterns:
                    test_url = f"{base_url}{pattern}"
                    try:
                        async with session.get(test_url, ssl=ssl_context, timeout=5) as response:
                            if response.status == 200:
                                api_info['has_api'] = True
                                api_info['endpoints'].append(test_url)
                                api_info['api_type'] = 'json_endpoint'
                                logger.info(f"✅ Found data endpoint: {test_url}")
                    except Exception:
                        continue
                
                # Check page source for API clues
                try:
                    async with session.get(url, ssl=ssl_context, timeout=10) as response:
                        content = await response.text()
                        
                        # Look for API keys or endpoints in JavaScript
                        api_matches = re.findall(r'["\']api["\']:\s*["\']([^"\']+)["\']', content)
                        endpoint_matches = re.findall(r'endpoint["\']:\s*["\']([^"\']+)["\']', content)
                        
                        for match in api_matches + endpoint_matches:
                            if match.startswith('http') or match.startswith('/'):
                                api_info['has_api'] = True
                                api_info['endpoints'].append(match)
                                
                        # Check for specific frameworks
                        if 'algolia' in content.lower():
                            api_info['api_type'] = 'algolia'
                            api_info['has_api'] = True
                            
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error(f"Error detecting API: {e}")
            
        self.detected_api = api_info
        return api_info
    
    async def extract_from_json_endpoint(
        self, 
        endpoint: str, 
        search_query: str = "",
        max_results: int = 500
    ) -> List[Dict[str, Any]]:
        """Extract data from JSON endpoint"""
        all_records = []
        
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, ssl=ssl_context) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Handle different JSON structures
                        items = []
                        if isinstance(data, list):
                            items = data
                        elif isinstance(data, dict):
                            # Look for common keys
                            for key in ['items', 'results', 'data', 'records', 'images']:
                                if key in data and isinstance(data[key], list):
                                    items = data[key]
                                    break
                        
                        # Parse items
                        for item in items[:max_results]:
                            if isinstance(item, dict):
                                record = {
                                    'title': item.get('title', item.get('name', '')),
                                    'description': item.get('description', item.get('caption', '')),
                                    'content_url': item.get('url', item.get('image_url', '')),
                                    'date_photo_taken': item.get('date', item.get('year', '')),
                                    'photographer': item.get('photographer', item.get('author', '')),
                                    'place_name': item.get('location', item.get('place', '')),
                                    'type': 'Image'
                                }
                                all_records.append(record)
                                
        except Exception as e:
            logger.error(f"Error extracting from JSON endpoint: {e}")
            
        return all_records
    
    async def extract(
        self, 
        url: str, 
        search_query: str = "",
        max_results: int = 500
    ) -> List[ArchiveRecord]:
        """
        Extract data using detected API
        """
        logger.info(f"🔌 API Detection Strategy: Extracting from {url}")
        
        # Detect API if not already done
        if not self.detected_api:
            await self.detect_api(url)
            
        if not self.detected_api['has_api']:
            logger.warning("No API detected, falling back to browser strategy")
            from src.strategies.browser_strategy import BrowserAutonomousStrategy
            fallback = BrowserAutonomousStrategy()
            return await fallback.extract(url, search_query, max_results)
        
        all_records = []
        
        # Try each detected endpoint
        for endpoint in self.detected_api['endpoints']:
            logger.info(f"Trying endpoint: {endpoint}")
            
            if self.detected_api['api_type'] == 'json_endpoint':
                records = await self.extract_from_json_endpoint(endpoint, search_query, max_results)
                all_records.extend(records)
                
                if len(all_records) >= max_results:
                    break
        
        # Filter by search query
        if search_query and all_records:
            all_records = self.filter_by_search_query(all_records, search_query)
        
        logger.info(f"✅ Extracted {len(all_records)} records via API")
        
        # Convert to ArchiveRecord objects
        return self.convert_to_archive_records(all_records)