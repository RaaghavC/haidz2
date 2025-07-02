#!/usr/bin/env python3
"""
Investigate ArchNet's Next.js API endpoints to find the actual data source.
"""

import requests
import json
import re
from urllib.parse import urljoin

class ArchNetNextJSInvestigator:
    """Investigate ArchNet's Next.js data structure."""
    
    def __init__(self):
        self.base_url = "https://www.archnet.org"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def investigate_nextjs_data(self):
        """Investigate Next.js data endpoints."""
        
        print("🔍 Investigating ArchNet Next.js Data Structure")
        print("=" * 60)
        
        # First, get the main page to find the build ID
        print("\n📍 Step 1: Getting build ID from main page...")
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # Look for build ID in the HTML
            build_id_pattern = r'"buildId":"([^"]+)"'
            build_id_match = re.search(build_id_pattern, response.text)
            
            if build_id_match:
                build_id = build_id_match.group(1)
                print(f"   ✓ Found build ID: {build_id}")
            else:
                # Try alternative pattern
                build_id_pattern2 = r'/_next/static/([^/]+)/_'
                build_id_match2 = re.search(build_id_pattern2, response.text)
                if build_id_match2:
                    build_id = build_id_match2.group(1)
                    print(f"   ✓ Found build ID (alt): {build_id}")
                else:
                    print("   ❌ Could not find build ID, using fallback")
                    build_id = "f1bHOLHS59BnqxI_3Itwz"  # From previous investigation
            
        except Exception as e:
            print(f"   ❌ Error getting main page: {e}")
            build_id = "f1bHOLHS59BnqxI_3Itwz"  # From previous investigation
        
        # Step 2: Try various Next.js data endpoints
        print(f"\n📍 Step 2: Testing Next.js data endpoints with build ID: {build_id}")
        
        data_endpoints = [
            f"/_next/data/{build_id}/en-US.json",
            f"/_next/data/{build_id}/sites.json",
            f"/_next/data/{build_id}/sites/category/all.json",
            f"/_next/data/{build_id}/sites/category/all/1.json",
            f"/_next/data/{build_id}/collections.json"
        ]
        
        for endpoint in data_endpoints:
            print(f"\n   🔗 Testing: {endpoint}")
            try:
                url = urljoin(self.base_url, endpoint)
                response = requests.get(url, headers=self.headers, timeout=30)
                
                if response.status_code == 200:
                    print(f"      ✅ SUCCESS! Status: {response.status_code}")
                    print(f"      Content-Type: {response.headers.get('content-type', 'unknown')}")
                    print(f"      Content-Length: {len(response.content)} bytes")
                    
                    try:
                        data = response.json()
                        print(f"      JSON Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        
                        # Save successful response for analysis
                        filename = f"archnet_nextjs_{endpoint.replace('/', '_').replace('?', '_')}.json"
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        print(f"      💾 Saved to: {filename}")
                        
                        # Analyze structure
                        self._analyze_data_structure(data, endpoint)
                        
                    except json.JSONDecodeError as e:
                        print(f"      ⚠️  JSON decode error: {e}")
                        print(f"      First 200 chars: {response.text[:200]}")
                
                else:
                    print(f"      ❌ Status: {response.status_code}")
            
            except requests.RequestException as e:
                print(f"      ❌ Request error: {e}")
        
        # Step 3: Try to find API patterns in page source
        print(f"\n📍 Step 3: Looking for API patterns in page source...")
        self._find_api_patterns_in_source()
    
    def _analyze_data_structure(self, data: dict, endpoint: str):
        """Analyze the structure of returned data."""
        print(f"      📊 Analyzing data structure for {endpoint}...")
        
        if isinstance(data, dict):
            if 'pageProps' in data:
                props = data['pageProps']
                print(f"         pageProps keys: {list(props.keys()) if isinstance(props, dict) else 'Not a dict'}")
                
                # Look for site/collection data
                for key in props.keys() if isinstance(props, dict) else []:
                    value = props[key]
                    if isinstance(value, list) and len(value) > 0:
                        print(f"         {key}: List with {len(value)} items")
                        if isinstance(value[0], dict):
                            print(f"            First item keys: {list(value[0].keys())}")
                    elif isinstance(value, dict):
                        print(f"         {key}: Dict with keys: {list(value.keys())}")
                    else:
                        print(f"         {key}: {type(value).__name__}")
    
    def _find_api_patterns_in_source(self):
        """Find API patterns in the page source."""
        print("   🔍 Scanning page source for API endpoints...")
        
        try:
            response = requests.get(f"{self.base_url}/sites", headers=self.headers, timeout=30)
            if response.status_code == 200:
                # Look for API endpoint patterns
                api_patterns = [
                    r'"/api/[^"]+',
                    r'"https://[^"]*api[^"]*',
                    r'/_next/data/[^"]+',
                    r'/graphql[^"]*',
                    r'fetch\([^)]+\)',
                    r'axios\.[a-z]+\([^)]+\)'
                ]
                
                found_apis = []
                for pattern in api_patterns:
                    matches = re.findall(pattern, response.text)
                    if matches:
                        found_apis.extend(matches)
                
                if found_apis:
                    print(f"   ✓ Found {len(found_apis)} potential API endpoints:")
                    for api in set(found_apis)[:10]:  # Show first 10 unique
                        print(f"      - {api}")
                else:
                    print("   ❌ No API patterns found in source")
            
        except Exception as e:
            print(f"   ❌ Error scanning source: {e}")

def main():
    """Main investigation function."""
    investigator = ArchNetNextJSInvestigator()
    investigator.investigate_nextjs_data()

if __name__ == "__main__":
    main()