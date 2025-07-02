#!/usr/bin/env python3
"""
Comprehensive ArchNet IIIF metadata extractor using the discovered patterns.
This extracts the ACTUAL detailed metadata that the user wants.
"""

import asyncio
import sys
import json
import requests
import subprocess
import tempfile
import os
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Any, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.browser_manager import BrowserManager
from src.models.schemas import ArchiveRecord
from src.modules.data_handler import DataHandler

class ArchNetIIIFExtractor:
    """Extract detailed metadata from ArchNet using IIIF standards and proper investigation."""
    
    def __init__(self):
        self.base_url = "https://www.archnet.org"
        self.iiif_base = "https://archnet-3-prod-iiif-cloud-c0fe51f0b9ac.herokuapp.com"
        self.browser_manager = BrowserManager()
        self.data_handler = DataHandler()
        self.extracted_records = []
        
    async def extract_comprehensive_metadata(self, max_sites: int = 50):
        """Extract comprehensive metadata from ArchNet using proper IIIF investigation."""
        
        print("🏛️  ArchNet Comprehensive IIIF Metadata Extraction")
        print("=" * 70)
        print(f"Target: Extract {max_sites} detailed records with full metadata")
        print("=" * 70)
        
        await self.browser_manager.start({"headless": False})
        
        try:
            async with self.browser_manager.create_page() as page:
                
                # Step 1: Get list of individual sites/buildings
                print("\n📍 Step 1: Finding individual site records...")
                site_urls = await self._get_individual_sites(page, max_sites)
                print(f"   ✓ Found {len(site_urls)} individual sites")
                
                # Step 2: Extract detailed metadata from each site
                print(f"\n📍 Step 2: Extracting detailed metadata from each site...")
                for i, site_url in enumerate(site_urls):
                    print(f"\n   📖 Processing site {i+1}/{len(site_urls)}: {site_url['title'][:50]}...")
                    
                    try:
                        record = await self._extract_site_metadata(page, site_url)
                        if record:
                            self.extracted_records.append(record)
                            print(f"      ✓ Extracted {len([k for k, v in record.items() if v])} populated fields")
                        else:
                            print(f"      ❌ Failed to extract metadata")
                            
                    except Exception as e:
                        print(f"      ❌ Error processing site: {e}")
                        continue
                    
                    # Take screenshot every 5 sites
                    if (i + 1) % 5 == 0:
                        await page.screenshot(path=f"archnet_extraction_progress_{i+1}.png")
                
                # Step 3: Save comprehensive results
                print(f"\n📍 Step 3: Saving {len(self.extracted_records)} comprehensive records...")
                await self._save_comprehensive_results()
                
        finally:
            await self.browser_manager.stop()
    
    async def _get_individual_sites(self, page, max_sites: int) -> List[Dict[str, str]]:
        """Get URLs of individual site/building pages."""
        site_urls = []
        
        # Navigate to sites listing with all sites
        sites_url = f"{self.base_url}/sites/category/all"
        await page.goto(sites_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)
        await page.screenshot(path="archnet_sites_listing.png")
        
        # Extract individual site links
        current_page = 1
        while len(site_urls) < max_sites:
            print(f"   📋 Scanning page {current_page} for site links...")
            
            # Get site links from current page
            page_sites = await page.evaluate("""
                () => {
                    const sites = [];
                    // Look for links to individual sites/buildings
                    const linkSelectors = [
                        'a[href*="/sites/"][href*="/"][href*="-"]',
                        'a[href*="/authorities/"]',
                        'a[href*="/collections/"]'
                    ];
                    
                    linkSelectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(link => {
                            if (link.href && link.textContent.trim() && 
                                !link.href.includes('/category/') && 
                                !link.href.includes('/search') &&
                                link.href !== window.location.href) {
                                
                                sites.push({
                                    url: link.href,
                                    title: link.textContent.trim(),
                                    type: 'site'
                                });
                            }
                        });
                    });
                    
                    // Remove duplicates
                    const unique = sites.filter((site, index, self) => 
                        index === self.findIndex(s => s.url === site.url)
                    );
                    
                    return unique;
                }
            """)
            
            new_sites = [site for site in page_sites if site['url'] not in [s['url'] for s in site_urls]]
            site_urls.extend(new_sites)
            
            print(f"      ✓ Found {len(new_sites)} new sites on page {current_page}")
            
            if len(site_urls) >= max_sites:
                break
            
            # Try to go to next page
            try:
                next_button = await page.query_selector('a[rel="next"], .pagination a:contains("Next"), a[aria-label="Next"]')
                if next_button:
                    await next_button.click()
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_timeout(3000)
                    current_page += 1
                else:
                    # No more pages
                    break
            except Exception as e:
                print(f"      ⚠️  Could not navigate to next page: {e}")
                break
        
        return site_urls[:max_sites]
    
    async def _extract_site_metadata(self, page, site_info: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Extract comprehensive metadata from an individual site page."""
        
        # Navigate to the individual site page
        await page.goto(site_info['url'], wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        
        # Extract comprehensive metadata
        metadata = await page.evaluate("""
            () => {
                const data = {};
                
                // Extract title (multiple selectors)
                const titleSelectors = ['h1', 'h2', '.page-title', '[class*="title"]', '.site-title'];
                for (const selector of titleSelectors) {
                    const element = document.querySelector(selector);
                    if (element && element.textContent.trim()) {
                        data.title = element.textContent.trim();
                        break;
                    }
                }
                
                // Extract description/summary
                const descSelectors = ['.description', '.summary', '[class*="description"]', '[class*="summary"]', '.content p'];
                for (const selector of descSelectors) {
                    const element = document.querySelector(selector);
                    if (element && element.textContent.trim()) {
                        data.description = element.textContent.trim();
                        break;
                    }
                }
                
                // Extract structured metadata (key-value pairs)
                data.metadata_pairs = {};
                
                // Look for definition lists
                const dtElements = document.querySelectorAll('dt');
                dtElements.forEach(dt => {
                    const dd = dt.nextElementSibling;
                    if (dd && dd.tagName === 'DD') {
                        const key = dt.textContent.trim().replace(':', '');
                        const value = dd.textContent.trim();
                        if (key && value) {
                            data.metadata_pairs[key] = value;
                        }
                    }
                });
                
                // Look for labeled fields
                const labeledFields = document.querySelectorAll('.field, [class*="metadata"], .property');
                labeledFields.forEach(field => {
                    const label = field.querySelector('.label, .key, [class*="label"]');
                    const value = field.querySelector('.value, .content, [class*="value"]');
                    if (label && value) {
                        const key = label.textContent.trim().replace(':', '');
                        const val = value.textContent.trim();
                        if (key && val) {
                            data.metadata_pairs[key] = val;
                        }
                    }
                });
                
                // Extract location information
                const locationSelectors = ['.location', '.address', '[class*="location"]', '[class*="address"]'];
                for (const selector of locationSelectors) {
                    const element = document.querySelector(selector);
                    if (element && element.textContent.trim()) {
                        data.location = element.textContent.trim();
                        break;
                    }
                }
                
                // Extract date information
                const dateSelectors = ['.date', '.year', '[class*="date"]', '[class*="year"]'];
                for (const selector of dateSelectors) {
                    const element = document.querySelector(selector);
                    if (element && element.textContent.trim()) {
                        data.date = element.textContent.trim();
                        break;
                    }
                }
                
                // Extract architect/creator information
                const creatorSelectors = ['.architect', '.creator', '.designer', '[class*="architect"]', '[class*="creator"]'];
                for (const selector of creatorSelectors) {
                    const element = document.querySelector(selector);
                    if (element && element.textContent.trim()) {
                        data.creator = element.textContent.trim();
                        break;
                    }
                }
                
                // Extract building type
                const typeSelectors = ['.type', '.category', '[class*="type"]', '[class*="category"]'];
                for (const selector of typeSelectors) {
                    const element = document.querySelector(selector);
                    if (element && element.textContent.trim()) {
                        data.building_type = element.textContent.trim();
                        break;
                    }
                }
                
                // Extract IIIF images with detailed information
                data.iiif_images = [];
                const images = document.querySelectorAll('img[src*="iiif"], img[src*="archnet"]');
                images.forEach(img => {
                    if (img.src && img.src.includes('iiif')) {
                        data.iiif_images.push({
                            src: img.src,
                            alt: img.alt || '',
                            title: img.title || '',
                            width: img.naturalWidth || img.width,
                            height: img.naturalHeight || img.height
                        });
                    }
                });
                
                // Check for structured data (JSON-LD)
                const jsonLd = document.querySelector('script[type="application/ld+json"]');
                if (jsonLd) {
                    try {
                        data.structured_data = JSON.parse(jsonLd.textContent);
                    } catch (e) {
                        // Ignore parsing errors
                    }
                }
                
                // Extract all text content for additional mining
                data.full_text = document.body.textContent.replace(/\\s+/g, ' ').trim();
                
                return data;
            }
        """)
        
        # Process and enhance the metadata
        enhanced_record = await self._enhance_metadata_with_iiif(metadata, site_info)
        
        return enhanced_record
    
    async def _enhance_metadata_with_iiif(self, base_metadata: Dict[str, Any], site_info: Dict[str, str]) -> Dict[str, Any]:
        """Enhance metadata using IIIF standards and ExifTool."""
        
        record = {
            'title': base_metadata.get('title', site_info.get('title', '')),
            'orig_location': base_metadata.get('location', ''),
            'collection': 'ArchNet',
            'inventory_num': self._extract_inventory_number(site_info['url']),
            'typ': base_metadata.get('building_type', 'Architecture'),
            'artist': base_metadata.get('creator', ''),
            'notes': base_metadata.get('description', ''),
            'image_url': ''
        }
        
        # Process IIIF images
        if base_metadata.get('iiif_images'):
            primary_image = base_metadata['iiif_images'][0]
            record['image_url'] = primary_image['src']
            
            # Extract additional metadata from image alt text
            alt_text = primary_image.get('alt', '')
            if alt_text:
                record['notes'] = alt_text if not record['notes'] else f"{record['notes']}. Image: {alt_text}"
            
            # Use IIIF to get image metadata
            iiif_metadata = await self._get_iiif_image_metadata(primary_image['src'])
            if iiif_metadata:
                record.update(iiif_metadata)
        
        # Process metadata pairs
        metadata_pairs = base_metadata.get('metadata_pairs', {})
        for key, value in metadata_pairs.items():
            # Map common fields
            key_lower = key.lower()
            if 'date' in key_lower or 'year' in key_lower:
                if not record.get('ce_start_date'):
                    record['ce_start_date'] = value
            elif 'location' in key_lower or 'place' in key_lower:
                if not record['orig_location']:
                    record['orig_location'] = value
            elif 'type' in key_lower or 'category' in key_lower:
                if not record['typ'] or record['typ'] == 'Architecture':
                    record['typ'] = value
            elif 'architect' in key_lower or 'designer' in key_lower or 'creator' in key_lower:
                if not record['artist']:
                    record['artist'] = value
        
        # Clean up empty fields
        for key, value in record.items():
            if isinstance(value, str):
                record[key] = value.strip() if value else ''
        
        return record
    
    async def _get_iiif_image_metadata(self, iiif_url: str) -> Optional[Dict[str, Any]]:
        """Extract metadata from IIIF image using IIIF standards and ExifTool."""
        metadata = {}
        
        try:
            # Try to get IIIF info.json
            base_url = iiif_url.replace('/iiif', '')
            info_url = f"{base_url}/info.json"
            
            response = requests.get(info_url, timeout=10)
            if response.status_code == 200:
                iiif_info = response.json()
                
                # Extract IIIF metadata
                if 'width' in iiif_info and 'height' in iiif_info:
                    metadata['measurements'] = f"{iiif_info['width']} x {iiif_info['height']} pixels"
                
                if 'attribution' in iiif_info:
                    metadata['copyright_for_photo'] = iiif_info['attribution']
                
                if 'metadata' in iiif_info:
                    for item in iiif_info['metadata']:
                        if isinstance(item, dict) and 'label' in item and 'value' in item:
                            label = item['label']
                            value = item['value']
                            
                            # Map IIIF metadata to our schema
                            if 'photographer' in label.lower():
                                metadata['photographer'] = value
                            elif 'date' in label.lower():
                                metadata['date_photograph_taken'] = value
                            elif 'medium' in label.lower():
                                metadata['medium'] = value
                            elif 'technique' in label.lower():
                                metadata['technique'] = value
        
        except Exception as e:
            print(f"      ⚠️  Could not extract IIIF metadata: {e}")
        
        # Try to use ExifTool for additional metadata
        try:
            # Download image to temp file
            image_response = requests.get(f"{iiif_url}/full/max/0/default.jpg", timeout=30)
            if image_response.status_code == 200:
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    temp_file.write(image_response.content)
                    temp_file_path = temp_file.name
                
                # Use ExifTool to extract metadata
                exif_result = subprocess.run([
                    'exiftool', '-json', '-all', temp_file_path
                ], capture_output=True, text=True)
                
                if exif_result.returncode == 0:
                    exif_data = json.loads(exif_result.stdout)[0]
                    
                    # Map EXIF data to our schema
                    if 'ImageWidth' in exif_data and 'ImageHeight' in exif_data:
                        metadata['measurements'] = f"{exif_data['ImageWidth']} x {exif_data['ImageHeight']} pixels"
                    
                    if 'Artist' in exif_data:
                        metadata['photographer'] = exif_data['Artist']
                    
                    if 'DateTime' in exif_data:
                        metadata['date_photograph_taken'] = exif_data['DateTime']
                    
                    if 'Copyright' in exif_data:
                        metadata['copyright_for_photo'] = exif_data['Copyright']
                
                # Clean up temp file
                os.unlink(temp_file_path)
        
        except Exception as e:
            print(f"      ⚠️  Could not extract EXIF metadata: {e}")
        
        return metadata
    
    def _extract_inventory_number(self, url: str) -> str:
        """Extract inventory number from URL."""
        # ArchNet URLs typically end with an ID
        parts = url.rstrip('/').split('/')
        if parts:
            return parts[-1]
        return ''
    
    async def _save_comprehensive_results(self):
        """Save the comprehensive results to CSV."""
        if not self.extracted_records:
            print("   ❌ No records to save")
            return
        
        # Convert to ArchiveRecord objects
        archive_records = []
        for record in self.extracted_records:
            try:
                archive_record = ArchiveRecord(**record)
                archive_records.append(archive_record)
            except Exception as e:
                print(f"   ⚠️  Skipping invalid record: {e}")
                continue
        
        if archive_records:
            output_file = "archnet_comprehensive_metadata.csv"
            self.data_handler.save_to_csv(archive_records, output_file)
            print(f"   ✅ Saved {len(archive_records)} comprehensive records to {output_file}")
            
            # Show sample
            print(f"\n📊 Sample of extracted comprehensive metadata:")
            for i, record in enumerate(archive_records[:3]):
                populated_fields = [k for k, v in record.__dict__.items() if v and v.strip()]
                print(f"   {i+1}. {record.title[:50]}...")
                print(f"      Populated fields: {len(populated_fields)}")
                print(f"      Location: {record.orig_location}")
                print(f"      Type: {record.typ}")
                print(f"      Artist: {record.artist}")
                print(f"      Measurements: {record.measurements}")
                print(f"      Date: {record.ce_start_date}")
        else:
            print("   ❌ No valid records to save")

async def main():
    """Main extraction function."""
    extractor = ArchNetIIIFExtractor()
    await extractor.extract_comprehensive_metadata(max_sites=20)  # Extract 20 sites for testing

if __name__ == "__main__":
    asyncio.run(main())