#!/usr/bin/env python3
"""
Comprehensive ArchNet investigation using IIIF standards and proper tools.
This script investigates the actual data structure of ArchNet to find detailed metadata.
"""

import asyncio
import sys
import json
import requests
import subprocess
from pathlib import Path
from urllib.parse import urljoin, urlparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.browser_manager import BrowserManager

class ArchNetInvestigator:
    """Comprehensive investigation of ArchNet using proper digital archive tools."""
    
    def __init__(self):
        self.base_url = "https://www.archnet.org"
        self.browser_manager = BrowserManager()
        self.findings = {
            'iiif_manifests': [],
            'api_endpoints': [],
            'image_urls': [],
            'metadata_patterns': [],
            'detailed_records': []
        }
    
    async def investigate_full_structure(self):
        """Comprehensive investigation of ArchNet's structure."""
        
        print("🔍 Starting comprehensive ArchNet investigation...")
        print("=" * 70)
        
        await self.browser_manager.start({"headless": False})
        
        try:
            async with self.browser_manager.create_page() as page:
                
                # Step 1: Investigate main page structure
                print("\n📍 Step 1: Investigating main page...")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(8000)
                await page.screenshot(path="investigate_01_main_page.png")
                
                # Look for IIIF endpoints
                await self._find_iiif_patterns(page)
                
                # Step 2: Navigate to Sites section
                print("\n📍 Step 2: Navigating to Sites section...")
                try:
                    sites_link = await page.query_selector("a[href*='sites'], nav a:has-text('Sites')")
                    if sites_link:
                        await sites_link.click()
                        await page.wait_for_load_state("domcontentloaded")
                        await page.wait_for_timeout(5000)
                        await page.screenshot(path="investigate_02_sites_section.png")
                    else:
                        # Try direct navigation
                        await page.goto(f"{self.base_url}/sites", wait_until="domcontentloaded")
                        await page.wait_for_timeout(5000)
                        await page.screenshot(path="investigate_02_sites_direct.png")
                except Exception as e:
                    print(f"   Error navigating to sites: {e}")
                
                # Step 3: Find individual records with detailed metadata
                print("\n📍 Step 3: Finding individual records...")
                await self._find_detailed_records(page)
                
                # Step 4: Investigate site list pages
                print("\n📍 Step 4: Investigating site listings...")
                await self._investigate_site_listings(page)
                
                # Step 5: Look for API endpoints and data sources
                print("\n📍 Step 5: Looking for API endpoints...")
                await self._find_api_endpoints(page)
                
                # Step 6: Test IIIF manifest access
                print("\n📍 Step 6: Testing IIIF manifest access...")
                await self._test_iiif_manifests()
                
        finally:
            await self.browser_manager.stop()
        
        # Step 7: Analyze findings and create extraction strategy
        print("\n📍 Step 7: Analyzing findings...")
        self._analyze_findings()
    
    async def _find_iiif_patterns(self, page):
        """Look for IIIF-related patterns and URLs."""
        print("   Looking for IIIF patterns...")
        
        # Check for IIIF URLs in page source
        page_content = await page.content()
        
        # Look for common IIIF patterns
        iiif_patterns = [
            'iiif', 'manifest.json', '/api/presentation/', '/iiif/',
            'universalviewer', 'mirador', '__NEXT_DATA__'
        ]
        
        for pattern in iiif_patterns:
            if pattern in page_content.lower():
                print(f"   ✓ Found IIIF pattern: {pattern}")
                self.findings['iiif_manifests'].append(pattern)
        
        # Extract IIIF URLs from JavaScript
        iiif_urls = await page.evaluate("""
            () => {
                const urls = [];
                const scripts = document.querySelectorAll('script');
                scripts.forEach(script => {
                    if (script.textContent.includes('iiif') || 
                        script.textContent.includes('manifest') ||
                        script.textContent.includes('__NEXT_DATA__')) {
                        urls.push({
                            type: 'script_content',
                            content: script.textContent.substring(0, 500) + '...'
                        });
                    }
                });
                
                // Look for image URLs that might be IIIF
                const images = document.querySelectorAll('img[src*="iiif"]');
                images.forEach(img => {
                    urls.push({
                        type: 'iiif_image',
                        src: img.src
                    });
                });
                
                return urls;
            }
        """)
        
        self.findings['iiif_manifests'].extend(iiif_urls)
        
        if iiif_urls:
            print(f"   ✓ Found {len(iiif_urls)} IIIF-related URLs")
    
    async def _find_detailed_records(self, page):
        """Find individual records with detailed metadata."""
        print("   Searching for detailed records...")
        
        # Look for individual site/building links
        site_links = await page.evaluate("""
            () => {
                const links = [];
                document.querySelectorAll('a[href*="/sites/"], a[href*="/building"], a[href*="/project"]').forEach(link => {
                    if (link.href && !links.includes(link.href)) {
                        links.push({
                            url: link.href,
                            text: link.textContent.trim(),
                            classes: link.className
                        });
                    }
                });
                return links.slice(0, 10); // First 10 links
            }
        """)
        
        print(f"   ✓ Found {len(site_links)} potential detailed record links")
        
        # Visit the first few to examine structure
        for i, link in enumerate(site_links[:3]):
            print(f"   📖 Investigating record {i+1}: {link['text'][:50]}...")
            try:
                await page.goto(link['url'], wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)
                await page.screenshot(path=f"investigate_03_record_{i+1}.png")
                
                # Extract detailed metadata from this page
                metadata = await self._extract_record_metadata(page)
                if metadata:
                    self.findings['detailed_records'].append({
                        'url': link['url'],
                        'title': link['text'],
                        'metadata': metadata
                    })
                
            except Exception as e:
                print(f"     ❌ Error investigating record: {e}")
    
    async def _extract_record_metadata(self, page):
        """Extract detailed metadata from an individual record page."""
        metadata = await page.evaluate("""
            () => {
                const data = {};
                
                // Look for structured metadata
                const metadataElements = document.querySelectorAll('[class*="metadata"], [class*="field"], .property, dt, dd');
                data.metadata_elements = metadataElements.length;
                
                // Look for title
                const titleSelectors = ['h1', 'h2', '[class*="title"]', '.page-title'];
                for (const selector of titleSelectors) {
                    const element = document.querySelector(selector);
                    if (element && element.textContent.trim()) {
                        data.title = element.textContent.trim();
                        break;
                    }
                }
                
                // Look for description
                const descSelectors = ['.description', '[class*="description"]', '.summary', '[class*="summary"]'];
                for (const selector of descSelectors) {
                    const element = document.querySelector(selector);
                    if (element && element.textContent.trim()) {
                        data.description = element.textContent.trim().substring(0, 200) + '...';
                        break;
                    }
                }
                
                // Look for images with IIIF URLs
                const images = document.querySelectorAll('img');
                data.images = [];
                images.forEach(img => {
                    if (img.src && (img.src.includes('iiif') || img.src.includes('archnet'))) {
                        data.images.push({
                            src: img.src,
                            alt: img.alt || '',
                            width: img.naturalWidth || img.width,
                            height: img.naturalHeight || img.height
                        });
                    }
                });
                
                // Look for location information
                const locationSelectors = ['.location', '[class*="location"]', '.address', '[class*="address"]'];
                for (const selector of locationSelectors) {
                    const element = document.querySelector(selector);
                    if (element && element.textContent.trim()) {
                        data.location = element.textContent.trim();
                        break;
                    }
                }
                
                // Look for date information
                const dateSelectors = ['.date', '[class*="date"]', '.year', '[class*="year"]'];
                for (const selector of dateSelectors) {
                    const element = document.querySelector(selector);
                    if (element && element.textContent.trim()) {
                        data.date = element.textContent.trim();
                        break;
                    }
                }
                
                // Check for structured data (JSON-LD, microdata)
                const jsonLd = document.querySelector('script[type="application/ld+json"]');
                if (jsonLd) {
                    try {
                        data.structured_data = JSON.parse(jsonLd.textContent);
                    } catch (e) {
                        data.structured_data_error = e.message;
                    }
                }
                
                return data;
            }
        """)
        
        print(f"     ✓ Found {metadata.get('metadata_elements', 0)} metadata elements")
        print(f"     ✓ Found {len(metadata.get('images', []))} images")
        
        return metadata
    
    async def _investigate_site_listings(self, page):
        """Investigate site listing pages for pagination and data structure."""
        print("   Investigating site listings...")
        
        # Try various listing pages
        listing_urls = [
            f"{self.base_url}/sites",
            f"{self.base_url}/sites/category/all",
            f"{self.base_url}/sites/category/all/1",
            f"{self.base_url}/collections",
            f"{self.base_url}/search"
        ]
        
        for url in listing_urls:
            try:
                print(f"   📋 Checking: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Count items on page
                item_count = await page.evaluate("""
                    () => {
                        const selectors = [
                            '[class*="item"]', '[class*="card"]', '[class*="result"]',
                            '[class*="site"]', '[class*="collection"]', 'article', 'li'
                        ];
                        let maxCount = 0;
                        for (const selector of selectors) {
                            const count = document.querySelectorAll(selector).length;
                            if (count > maxCount && count < 200) { // Reasonable range
                                maxCount = count;
                            }
                        }
                        return maxCount;
                    }
                """)
                
                if item_count > 5:
                    print(f"     ✓ Found {item_count} items on this page")
                    await page.screenshot(path=f"investigate_04_listing_{urlparse(url).path.replace('/', '_')}.png")
                
            except Exception as e:
                print(f"     ❌ Error checking {url}: {e}")
    
    async def _find_api_endpoints(self, page):
        """Look for API endpoints and data sources."""
        print("   Looking for API endpoints...")
        
        # Monitor network requests to find API calls
        api_calls = []
        
        page.on("response", lambda response: api_calls.append({
            'url': response.url,
            'status': response.status,
            'content_type': response.headers.get('content-type', ''),
            'method': response.request.method
        }) if any(keyword in response.url.lower() for keyword in ['api', 'json', 'iiif', 'search', 'query']) else None)
        
        # Trigger some interactions to capture API calls
        try:
            # Try searching
            search_input = await page.query_selector('input[type="search"], input[placeholder*="Search"]')
            if search_input:
                await search_input.fill("mosque")
                search_button = await page.query_selector('button[type="submit"], .search-button')
                if search_button:
                    await search_button.click()
                    await page.wait_for_timeout(3000)
            
            # Try navigation
            nav_links = await page.query_selector_all('nav a, .pagination a')
            if nav_links and len(nav_links) > 0:
                await nav_links[0].click()
                await page.wait_for_timeout(2000)
        
        except Exception:
            pass
        
        # Wait a bit more for network requests
        await page.wait_for_timeout(5000)
        
        if api_calls:
            print(f"   ✓ Captured {len(api_calls)} API calls")
            self.findings['api_endpoints'].extend(api_calls)
            
            for call in api_calls[:5]:  # Show first 5
                print(f"     - {call['method']} {call['url'][:80]}...")
    
    async def _test_iiif_manifests(self):
        """Test access to IIIF manifests."""
        print("   Testing IIIF manifest access...")
        
        # Common IIIF manifest patterns for ArchNet
        manifest_patterns = [
            f"{self.base_url}/iiif/manifest.json",
            f"{self.base_url}/api/iiif/manifest.json",
            f"{self.base_url}/iiif/presentation/manifest.json",
        ]
        
        for pattern in manifest_patterns:
            try:
                response = requests.get(pattern, timeout=10)
                if response.status_code == 200:
                    print(f"   ✓ Found IIIF manifest: {pattern}")
                    self.findings['iiif_manifests'].append({
                        'url': pattern,
                        'status': response.status_code,
                        'content_type': response.headers.get('content-type', ''),
                        'size': len(response.content)
                    })
            except Exception:
                pass
    
    def _analyze_findings(self):
        """Analyze all findings and provide extraction strategy."""
        print("\n" + "=" * 70)
        print("📊 INVESTIGATION FINDINGS SUMMARY")
        print("=" * 70)
        
        print(f"\n🔍 IIIF Patterns Found: {len(self.findings['iiif_manifests'])}")
        for pattern in self.findings['iiif_manifests'][:5]:
            if isinstance(pattern, dict):
                print(f"   - {pattern.get('type', 'unknown')}: {str(pattern)[:80]}...")
            else:
                print(f"   - {pattern}")
        
        print(f"\n🌐 API Endpoints Found: {len(self.findings['api_endpoints'])}")
        for endpoint in self.findings['api_endpoints'][:5]:
            print(f"   - {endpoint['method']} {endpoint['url'][:60]}...")
        
        print(f"\n📖 Detailed Records Analyzed: {len(self.findings['detailed_records'])}")
        for record in self.findings['detailed_records']:
            print(f"   - {record['title'][:50]}... ({len(record['metadata'])} metadata fields)")
        
        # Save findings to file
        with open('archnet_investigation_findings.json', 'w', encoding='utf-8') as f:
            json.dump(self.findings, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Full findings saved to: archnet_investigation_findings.json")
        
        # Provide extraction strategy recommendations
        print(f"\n🎯 EXTRACTION STRATEGY RECOMMENDATIONS:")
        print("   1. Use network monitoring to capture API endpoints during navigation")
        print("   2. Look for IIIF image URLs in individual record pages")
        print("   3. Extract metadata from detailed record pages, not just listing pages")
        print("   4. Use the captured API endpoints for bulk data extraction")
        print("   5. Implement proper IIIF manifest parsing for image metadata")

async def main():
    """Main investigation function."""
    investigator = ArchNetInvestigator()
    await investigator.investigate_full_structure()

if __name__ == "__main__":
    asyncio.run(main())