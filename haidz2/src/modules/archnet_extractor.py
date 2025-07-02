"""
Special extractor for ArchNet that handles their React/Next.js architecture.
"""

import json
import re
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
import httpx


class ArchNetExtractor:
    """Optimized extractor for ArchNet's server-side rendered content."""
    
    def __init__(self):
        self.base_url = "https://www.archnet.org"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        }
        
    def extract_sites_list(self, page_num: int = 1) -> List[Dict[str, Any]]:
        """Extract sites from the list page using direct HTTP requests."""
        # ArchNet uses category-based URLs
        url = f"{self.base_url}/sites/category/all/{page_num}"
        
        try:
            # Use a session with cookies and better compatibility
            with httpx.Client(timeout=60.0, headers=self.headers, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                
                # Debug: check if we got the data
                if '__NEXT_DATA__' not in response.text:
                    print("Warning: __NEXT_DATA__ not found in response")
                
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract data from __NEXT_DATA__ script tag
            script_tag = soup.find('script', id='__NEXT_DATA__')
            if not script_tag:
                # Try different selector
                script_tag = soup.find('script', {'type': 'application/json'})
            
            if script_tag:
                try:
                    data = json.loads(script_tag.string)
                    # Navigate to the sites data
                    page_props = data.get('props', {}).get('pageProps', {})
                    sites = page_props.get('sites', [])
                    
                    extracted_sites = []
                    for site in sites:
                        # Extract image URL
                        image_url = ''
                        primary_image = site.get('primary_image', {})
                        if primary_image and primary_image.get('child'):
                            child = primary_image['child']
                            image_url = child.get('content_url', '')
                        
                        # Extract location - it's directly in place_name
                        location = site.get('place_name', '')
                        
                        extracted_sites.append({
                            'id': site.get('id'),
                            'title': site.get('name', ''),
                            'location': location,
                            'url': f"{self.base_url}/sites/{site.get('id')}",
                            'image_url': image_url,
                            'collection': 'ArchNet',
                            'inventory_num': str(site.get('id', '')),
                            'type': site.get('site_types', [{}])[0].get('name', '') if site.get('site_types') else '',
                            'description': site.get('notes', '')
                        })
                    
                    return extracted_sites
                except json.JSONDecodeError:
                    pass
            
            # Fallback to HTML parsing if __NEXT_DATA__ is not available
            return self._extract_from_html(soup)
            
        except Exception as e:
            print(f"Error extracting ArchNet sites: {e}")
            return []
    
    def _extract_from_html(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Fallback HTML extraction."""
        sites = []
        
        # Look for site cards/items - ArchNet specific selectors
        selectors = [
            'a.ui.link.card', '.ui.card', '[class*="card"]',
            '.site-item', '.collection-item',
            'article', '.grid-item', '[class*="result"]',
            'div[class*="cards"] > a'
        ]
        
        for selector in selectors:
            items = soup.select(selector)
            if items:
                for item in items:
                    site_data = {}
                    
                    # Extract title
                    title_elem = item.select_one('h2, h3, .title, .name, a')
                    if title_elem:
                        site_data['title'] = title_elem.get_text(strip=True)
                    
                    # Extract location
                    location_elem = item.select_one('.location, [class*="location"]')
                    if location_elem:
                        site_data['location'] = location_elem.get_text(strip=True)
                    
                    # Extract link
                    link_elem = item.select_one('a[href]')
                    if link_elem:
                        href = link_elem.get('href', '')
                        if href:
                            site_data['url'] = self.base_url + href if href.startswith('/') else href
                            # Extract ID from URL
                            id_match = re.search(r'/sites/(\d+)', href)
                            if id_match:
                                site_data['id'] = id_match.group(1)
                                site_data['inventory_num'] = id_match.group(1)
                    
                    # Extract image
                    img_elem = item.select_one('img')
                    if img_elem:
                        img_src = img_elem.get('src', '')
                        if img_src:
                            site_data['image_url'] = self.base_url + img_src if img_src.startswith('/') else img_src
                    
                    site_data['collection'] = 'ArchNet'
                    
                    if site_data.get('title'):
                        sites.append(site_data)
                
                break
        
        return sites
    
    def extract_site_details(self, site_id: str) -> Dict[str, Any]:
        """Extract detailed information about a specific site."""
        url = f"{self.base_url}/sites/{site_id}"
        
        try:
            with httpx.Client(timeout=30.0, headers=self.headers) as client:
                response = client.get(url)
                response.raise_for_status()
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to extract from __NEXT_DATA__
            script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
            if script_tag:
                try:
                    data = json.loads(script_tag.string)
                    site_data = data.get('props', {}).get('pageProps', {}).get('site', {})
                    
                    # Extract all available fields
                    extracted = {
                        'id': site_data.get('id', site_id),
                        'title': site_data.get('name', ''),
                        'location': site_data.get('location', ''),
                        'description': site_data.get('description', ''),
                        'type': site_data.get('type', ''),
                        'date': site_data.get('date', ''),
                        'dimensions': site_data.get('dimensions', ''),
                        'collection': 'ArchNet',
                        'inventory_num': str(site_data.get('id', site_id)),
                        'images': []
                    }
                    
                    # Extract images
                    media = site_data.get('media', [])
                    for m in media:
                        if m.get('type') == 'image':
                            extracted['images'].append({
                                'url': m.get('url', ''),
                                'caption': m.get('caption', ''),
                                'id': m.get('id', '')
                            })
                    
                    return extracted
                    
                except json.JSONDecodeError:
                    pass
            
            # Fallback to HTML parsing
            return self._extract_details_from_html(soup, site_id)
            
        except Exception as e:
            print(f"Error extracting site details: {e}")
            return {}
    
    def _extract_details_from_html(self, soup: BeautifulSoup, site_id: str) -> Dict[str, Any]:
        """Extract details from HTML."""
        details = {
            'id': site_id,
            'collection': 'ArchNet',
            'inventory_num': site_id
        }
        
        # Extract title
        title_elem = soup.select_one('h1')
        if title_elem:
            details['title'] = title_elem.get_text(strip=True)
            # Extract location from subtitle
            sub_elem = title_elem.select_one('.sub')
            if sub_elem:
                details['location'] = sub_elem.get_text(strip=True)
        
        # Extract description
        desc_elem = soup.select_one('.rich-text p')
        if desc_elem:
            details['description'] = desc_elem.get_text(strip=True)
        
        # Extract other metadata
        for section in soup.select('h2'):
            section_title = section.get_text(strip=True).lower()
            next_elem = section.find_next_sibling()
            
            if next_elem:
                if 'dimension' in section_title:
                    details['dimensions'] = next_elem.get_text(strip=True)
                elif 'event' in section_title or 'date' in section_title:
                    details['date'] = next_elem.get_text(strip=True)
                elif 'type' in section_title:
                    details['type'] = next_elem.get_text(strip=True)
        
        return details