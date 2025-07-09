"""
Resource Verifier Module to validate content type before extraction.
Ensures we only process Image resources and filter out Collections, Authorities, etc.
"""

import logging
import re
from typing import Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
from datetime import datetime

from openai import OpenAI
from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

# Set up logging
logger = logging.getLogger(__name__)


class ResourceVerifier:
    """
    Verifies that a resource is of the correct type (Image) and meets our criteria.
    """
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "openai"):
        """
        Initialize the verifier with LLM provider.
        
        Args:
            api_key: API key for the LLM provider
            provider: LLM provider to use ('openai' or 'anthropic')
        """
        self.provider = provider
        
        if provider == "openai":
            self.client = OpenAI(api_key=api_key)
            self.model = "gpt-4-turbo-preview"
        elif provider == "anthropic":
            self.client = Anthropic(api_key=api_key)
            self.model = "claude-3-opus-20240229"
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        logger.info(f"Initialized ResourceVerifier with {provider} provider")
    
    def _extract_text_content(self, html: str) -> str:
        """
        Extract relevant text content from HTML for analysis.
        
        Args:
            html: Raw HTML content
            
        Returns:
            Extracted text content
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get the page title
        title = soup.find('title')
        title_text = title.get_text(strip=True) if title else ""
        
        # Look for key indicators
        text_content = f"Title: {title_text}\n"
        
        # Extract headings
        for heading in soup.find_all(['h1', 'h2', 'h3']):
            text_content += f"Heading: {heading.get_text(strip=True)}\n"
        
        # Look for meta descriptions
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            text_content += f"Description: {meta_desc.get('content', '')}\n"
        
        # Look for breadcrumbs or navigation that might indicate type
        breadcrumbs = soup.find_all(class_=re.compile(r'breadcrumb|crumb|navigation', re.I))
        for crumb in breadcrumbs[:3]:  # Limit to first 3
            text_content += f"Navigation: {crumb.get_text(strip=True)}\n"
        
        # Look for type indicators
        type_indicators = soup.find_all(text=re.compile(r'\b(image|photo|photograph|picture|collection|authority|site)\b', re.I))
        for indicator in type_indicators[:5]:  # Limit to first 5
            text_content += f"Type indicator: {indicator.strip()}\n"
        
        # Look for image elements
        images = soup.find_all('img')
        text_content += f"Number of images: {len(images)}\n"
        
        # Sample first few image alt texts
        for img in images[:3]:
            alt = img.get('alt', '')
            if alt:
                text_content += f"Image alt: {alt}\n"
        
        return text_content[:2000]  # Limit total content
    
    def _quick_type_check(self, html: str, url: Optional[str] = None) -> Tuple[str, float]:
        """
        Perform a quick heuristic check for resource type.
        
        Args:
            html: Raw HTML content
            url: Optional URL of the page for pattern matching
            
        Returns:
            Tuple of (detected_type, confidence_score)
        """
        text = html.lower()
        soup = BeautifulSoup(html, 'lxml')
        
        # SPECIAL CASE: ArchNet image URLs with media_content_id
        if url and 'media_content_id=' in url:
            # This is definitely an image page on ArchNet
            return 'image', 0.95
        
        # Count various indicators
        image_indicators = 0
        collection_indicators = 0
        authority_indicators = 0
        site_indicators = 0
        
        # Check page title
        title = soup.find('title')
        if title:
            title_text = title.get_text(strip=True).lower()
            if 'collection' in title_text:
                collection_indicators += 3
            elif 'authority' in title_text or 'person' in title_text:
                authority_indicators += 3
            elif 'site' in title_text or 'location' in title_text:
                site_indicators += 3
            elif any(word in title_text for word in ['photo', 'image', 'picture']):
                image_indicators += 3
        
        # Check for image elements
        images = soup.find_all('img')
        if len(images) > 0:
            image_indicators += min(len(images), 5)  # Cap at 5
        
        # Check for gallery or viewer elements
        if soup.find(class_=re.compile(r'gallery|viewer|image-container|photo', re.I)):
            image_indicators += 2
        
        # Check breadcrumbs or type indicators
        type_elements = soup.find_all(text=re.compile(r'\btype\s*:\s*(\w+)', re.I))
        for elem in type_elements:
            match = re.search(r'\btype\s*:\s*(\w+)', elem, re.I)
            if match:
                type_value = match.group(1).lower()
                if 'image' in type_value or 'photo' in type_value:
                    image_indicators += 5
                elif 'collection' in type_value:
                    collection_indicators += 5
                elif 'authority' in type_value:
                    authority_indicators += 5
                elif 'site' in type_value:
                    site_indicators += 5
        
        # Check URL patterns
        if 'collection' in text[:1000]:  # Check early in page
            collection_indicators += 1
        if 'authority' in text[:1000]:
            authority_indicators += 1
        
        # Determine type based on indicators
        scores = {
            'image': image_indicators,
            'collection': collection_indicators,
            'authority': authority_indicators,
            'site': site_indicators
        }
        
        # Get the type with highest score
        detected_type = max(scores, key=scores.get)
        max_score = scores[detected_type]
        
        # Calculate confidence (0-1)
        total_score = sum(scores.values()) or 1
        confidence = max_score / total_score if max_score > 0 else 0.0
        
        return detected_type, confidence
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
    async def verify_resource_type(self, html: str, url: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify the resource type using LLM analysis.
        
        Args:
            html: Raw HTML content of the page
            url: Optional URL of the page for pattern matching
            
        Returns:
            Dictionary with verification results
        """
        # First do a quick heuristic check
        quick_type, quick_confidence = self._quick_type_check(html, url)
        
        # If we're very confident about the type, skip LLM check
        if quick_confidence > 0.8:
            is_image = quick_type == 'image'
            return {
                'is_image': is_image,
                'resource_type': quick_type,
                'confidence': quick_confidence,
                'reason': f"Quick check determined this is a {quick_type} resource",
                'should_extract': is_image,
                'has_metadata': is_image  # Assume ArchNet images have metadata
            }
        
        # Extract key content for LLM analysis
        text_content = self._extract_text_content(html)
        
        # Create prompt for LLM
        prompt = f"""Analyze the following web page content and determine if this is an IMAGE resource (a single photograph, artwork, or visual item) 
versus a COLLECTION (group of items), AUTHORITY (person/organization record), or SITE (location/building record).

IMPORTANT: We only want to extract data from IMAGE resources - individual photos or artworks with metadata.

Content to analyze:
{text_content}

Provide your analysis in the following format:
1. Resource Type: [IMAGE/COLLECTION/AUTHORITY/SITE/OTHER]
2. Confidence: [0-100]%
3. Reason: [Brief explanation]
4. Has Image Metadata: [YES/NO] (title, date, photographer, etc.)
5. Should Extract: [YES/NO] (only YES for IMAGE type with metadata)

Be very strict - only classify as IMAGE if this is clearly a single photograph or artwork page, not a gallery or collection page."""
        
        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert at analyzing museum and archive websites."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=500
                )
                
                analysis = response.choices[0].message.content
                
            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=500
                )
                
                analysis = response.content[0].text
            
            # Parse the analysis
            lines = analysis.strip().split('\n')
            result = {
                'is_image': False,
                'resource_type': 'unknown',
                'confidence': 0.0,
                'reason': '',
                'has_metadata': False,
                'should_extract': False
            }
            
            for line in lines:
                line_lower = line.lower()
                if 'resource type:' in line_lower:
                    if 'image' in line_lower:
                        result['resource_type'] = 'image'
                        result['is_image'] = True
                    elif 'collection' in line_lower:
                        result['resource_type'] = 'collection'
                    elif 'authority' in line_lower:
                        result['resource_type'] = 'authority'
                    elif 'site' in line_lower:
                        result['resource_type'] = 'site'
                
                elif 'confidence:' in line_lower:
                    # Extract percentage
                    match = re.search(r'(\d+)', line)
                    if match:
                        result['confidence'] = float(match.group(1)) / 100.0
                
                elif 'reason:' in line_lower:
                    result['reason'] = line.split(':', 1)[1].strip()
                
                elif 'has image metadata:' in line_lower:
                    result['has_metadata'] = 'yes' in line_lower
                
                elif 'should extract:' in line_lower:
                    result['should_extract'] = 'yes' in line_lower
            
            logger.info(f"Resource verification: Type={result['resource_type']}, "
                       f"Confidence={result['confidence']:.2f}, "
                       f"Should Extract={result['should_extract']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in LLM verification: {str(e)}")
            # Fall back to heuristic result
            return {
                'is_image': quick_type == 'image',
                'resource_type': quick_type,
                'confidence': quick_confidence,
                'reason': 'LLM verification failed, using heuristic check',
                'should_extract': quick_type == 'image' and quick_confidence > 0.6
            }
    
    def verify_location(self, location_text: str) -> Dict[str, bool]:
        """
        Verify if a location is specifically Antakya (not general Hatay or Syria).
        
        Args:
            location_text: Location text to verify
            
        Returns:
            Dictionary with location verification results
        """
        if not location_text:
            return {
                'is_antakya': False,
                'is_pre_earthquake': True,  # Assume old if no location
                'reason': 'No location specified'
            }
        
        location_lower = location_text.lower()
        
        # Check for Antakya specifically
        is_antakya = 'antakya' in location_lower or 'antioch' in location_lower
        
        # Exclude if it's just Hatay without Antakya
        if 'hatay' in location_lower and not is_antakya:
            return {
                'is_antakya': False,
                'is_pre_earthquake': True,
                'reason': 'Location is Hatay province but not specifically Antakya'
            }
        
        # Exclude Syria locations
        if 'syria' in location_lower or 'سوريا' in location_text:
            return {
                'is_antakya': False,
                'is_pre_earthquake': True,
                'reason': 'Location is in Syria, not Turkey'
            }
        
        # Check for earthquake-related content
        earthquake_keywords = ['earthquake', 'deprem', '2023', 'damage', 'destroyed', 'rubble']
        is_earthquake_related = any(keyword in location_lower for keyword in earthquake_keywords)
        
        return {
            'is_antakya': is_antakya,
            'is_pre_earthquake': not is_earthquake_related,
            'reason': 'Valid Antakya location' if is_antakya else 'Not Antakya'
        }
    
    def verify_date(self, date_text: str) -> Dict[str, bool]:
        """
        Verify if a date is pre-2023 earthquake.
        
        Args:
            date_text: Date text to verify
            
        Returns:
            Dictionary with date verification results
        """
        if not date_text:
            return {
                'is_valid': True,
                'is_pre_earthquake': True,
                'reason': 'No date specified, assuming historical'
            }
        
        # Check for 2023 or later
        if '2023' in date_text or '2024' in date_text or '2025' in date_text:
            # Check if it's about the earthquake
            if any(word in date_text.lower() for word in ['earthquake', 'deprem', 'damage']):
                return {
                    'is_valid': False,
                    'is_pre_earthquake': False,
                    'reason': 'Post-earthquake content from 2023 or later'
                }
        
        # Extract year using regex
        year_match = re.search(r'\b(19\d{2}|20[0-2][0-9])\b', date_text)
        if year_match:
            year = int(year_match.group(1))
            if year >= 2023:
                return {
                    'is_valid': False,
                    'is_pre_earthquake': False,
                    'reason': f'Date {year} is during or after earthquake'
                }
        
        return {
            'is_valid': True,
            'is_pre_earthquake': True,
            'reason': 'Date is pre-earthquake or historical'
        }