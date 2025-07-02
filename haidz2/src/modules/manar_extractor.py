"""
Special extractor for Manar al-Athar Oxford archive.
"""

from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
import httpx
import re


class ManarExtractor:
    """Optimized extractor for Manar al-Athar archive."""
    
    def __init__(self):
        self.base_url = "https://www.manar-al-athar.ox.ac.uk"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        }
        
    def extract_search_results(self, page_num: int = 1, per_page: int = 48) -> List[Dict[str, Any]]:
        """Extract photos from the search results page."""
        # Manar uses search.php for browsing all photos
        url = f"{self.base_url}/pages/search.php"
        
        # Parameters for pagination
        params = {
            'per_page': per_page,
            'page': page_num,
            'orderby': 'resourcetype,field8',  # Original filename order
            'sort': 'ASC'
        }
        
        try:
            with httpx.Client(timeout=60.0, headers=self.headers, follow_redirects=True) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            photos = []
            
            # Find photo containers - they appear to be in a grid
            photo_containers = soup.find_all('div', class_=['item', 'result-item'])
            
            # If no specific containers found, look for TIF references
            if not photo_containers:
                # Look for image thumbnails and metadata
                thumbnails = soup.find_all('img', src=re.compile(r'preview'))
                for thumb in thumbnails:
                    parent = thumb.find_parent(['div', 'td', 'li'])
                    if parent:
                        photo_containers.append(parent)
            
            # If still no containers, look for filename patterns
            if not photo_containers:
                # Look for elements containing .tif filenames
                tif_elements = soup.find_all(text=re.compile(r'\.tif', re.IGNORECASE))
                for tif_text in tif_elements:
                    if hasattr(tif_text, 'parent'):
                        parent = tif_text.parent.find_parent(['div', 'td', 'li'])
                        if parent and parent not in photo_containers:
                            photo_containers.append(parent)
            
            print(f"Found {len(photo_containers)} photo containers")
            
            for container in photo_containers:
                try:
                    photo_data = self._extract_photo_metadata(container)
                    if photo_data:
                        photos.append(photo_data)
                except Exception as e:
                    print(f"Error extracting photo metadata: {e}")
                    continue
            
            return photos
            
        except Exception as e:
            print(f"Error fetching Manar search results: {e}")
            return []
    
    def _extract_photo_metadata(self, container) -> Optional[Dict[str, Any]]:
        """Extract metadata from a photo container."""
        data = {}
        
        # Skip containers with JavaScript code
        container_text = container.get_text()
        if 'jQuery' in container_text or 'javascript' in container_text.lower():
            return None
        
        # Extract filename - look for .tif files in the container
        tif_matches = re.findall(r'(\w+\.tif)', container_text, re.IGNORECASE)
        if tif_matches:
            filename = tif_matches[0]
            data['inventory_num'] = filename
            data['title'] = filename.replace('.tif', '').replace('.TIF', '')
        else:
            # Skip if no filename found
            return None
        
        # Extract location/description text - look for meaningful location names
        text_elements = container.find_all(text=True)
        location_candidates = []
        
        for text in text_elements:
            text_clean = text.strip()
            # Filter out JavaScript, UI elements, and filenames
            if (text_clean and len(text_clean) > 3 and 
                not text_clean.endswith('.tif') and 
                not text_clean.lower().startswith('tif') and
                'jQuery' not in text_clean and
                'javascript' not in text_clean.lower() and
                text_clean.lower() not in ['actions...', 'refine results', 'page', 'of', 'results']):
                
                # Look for location-like text (proper nouns, place names)
                if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', text_clean):
                    location_candidates.append(text_clean)
        
        # Use the most reasonable location candidate
        if location_candidates:
            # Prefer shorter, more specific location names
            location = min(location_candidates, key=len)
            if len(location) <= 50:  # Reasonable location name length
                data['location'] = location
        
        # Extract image URL
        img = container.find('img')
        if img and img.get('src'):
            img_src = img['src']
            if not img_src.startswith('http'):
                img_src = f"{self.base_url}/{img_src.lstrip('/')}"
            data['image_url'] = img_src
        
        # Set collection and type
        data['collection'] = 'Manar al-Athar'
        data['type'] = 'Photograph'
        
        return data
    
    def get_total_results(self) -> int:
        """Get the total number of results available."""
        try:
            url = f"{self.base_url}/pages/search.php"
            
            with httpx.Client(timeout=60.0, headers=self.headers, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for result count text
            result_text = soup.find(text=re.compile(r'\d+\s+results'))
            if result_text:
                # Extract number from text like "84,058 results"
                numbers = re.findall(r'[\d,]+', result_text)
                if numbers:
                    return int(numbers[0].replace(',', ''))
            
            return 0
            
        except Exception as e:
            print(f"Error getting total results: {e}")
            return 0