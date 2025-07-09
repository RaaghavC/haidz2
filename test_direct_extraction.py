#!/usr/bin/env python3
"""
Direct test of vision-based extraction on a known image detail page.
This tests the core vision extraction capability.
"""

import asyncio
import os
import sys
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.modules.vision_extractor import VisionBasedExtractor
from src.modules.image_verifier import ImageVerifier
from src.models.schemas import ArchiveRecord
from src.utils.stealth_browser_manager import StealthBrowserManager
import openai


async def test_direct_extraction():
    """Test direct extraction from a known image page."""
    
    # Test URLs - these are direct image detail pages
    test_urls = [
        "https://archnet.org/sites/5416?media_content_id=122765",  # Antakya example
        "https://www.archnet.org/sites/2055",  # Another example
    ]
    
    # Initialize components
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set!")
        return
    
    client = openai.Client(api_key=api_key)
    browser = StealthBrowserManager(headless=False)  # Show browser for debugging
    extractor = VisionBasedExtractor(client)
    verifier = ImageVerifier(client)
    
    print("DIRECT VISION EXTRACTION TEST")
    print("=" * 60)
    
    await browser.start()
    
    for url in test_urls:
        print(f"\nTesting: {url}")
        print("-" * 40)
        
        try:
            async with browser.new_page() as page:
                # Navigate to page
                print("Loading page...")
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                
                # Take screenshot for debugging
                await page.screenshot(path=f"screenshots/test_page_{url.split('/')[-1]}.png")
                
                # Verify it's an image page
                print("Verifying page type...")
                is_image_page = await verifier.verify_page(page)
                print(f"Is image detail page: {is_image_page}")
                
                if is_image_page:
                    # Extract data
                    print("\nExtracting data with vision...")
                    data = await extractor.extract_with_vision(
                        page,
                        ArchiveRecord,
                        "Extract all available metadata for the historical architecture image shown on this page. Include title, location, dates, photographer, collection, and any other relevant information."
                    )
                    
                    print("\nExtracted Data:")
                    for key, value in data.items():
                        if value is not None and value != "":
                            print(f"  {key}: {value}")
                    
                    # Calculate completeness
                    total_fields = len(data)
                    filled_fields = sum(1 for v in data.values() if v is not None and v != "")
                    print(f"\nCompleteness: {filled_fields}/{total_fields} fields ({filled_fields/total_fields*100:.1f}%)")
                else:
                    print("Page not recognized as image detail page")
                
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    await browser.stop()
    print("\n\nTest complete!")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run test
    asyncio.run(test_direct_extraction())