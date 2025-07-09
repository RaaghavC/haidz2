#!/usr/bin/env python3
"""
Test with real, verified working pages.
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agent.true_agentic_orchestrator import TrueAgenticOrchestrator
from src.agent.config import AgentConfig
from src.modules.vision_extractor import VisionBasedExtractor
from src.modules.image_verifier import ImageVerifier
from src.models.schemas import ArchiveRecord
from src.utils.stealth_browser_manager import StealthBrowserManager
import openai


async def test_real_page():
    """Test with a real page we can verify exists."""
    
    # Start with Wikipedia page about Antakya to find real image links
    test_url = "https://en.wikipedia.org/wiki/Antakya"
    
    client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))
    browser = StealthBrowserManager(headless=False)
    extractor = VisionBasedExtractor(client)
    verifier = ImageVerifier(client)
    
    print("TEST: Finding and extracting from real pages")
    print("=" * 60)
    
    await browser.start()
    
    try:
        async with browser.new_page() as page:
            print(f"Loading Wikipedia page: {test_url}")
            await page.goto(test_url, wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            # Find an image on the page
            print("Looking for images...")
            first_image = await page.query_selector('img[src*="upload.wikimedia.org"]')
            
            if first_image:
                # Click on the image to go to its page
                print("Clicking on first image...")
                await first_image.click()
                await page.wait_for_timeout(3000)
                
                current_url = page.url
                print(f"Current URL: {current_url}")
                
                # Check if we're on an image detail page
                is_image_page = await verifier.verify_page(page)
                print(f"Is image detail page: {is_image_page}")
                
                if is_image_page:
                    print("\nExtracting data...")
                    data = await extractor.extract_with_vision(
                        page,
                        ArchiveRecord,
                        "Extract all metadata for this image including title, description, date, photographer, location, and license information. This is a Wikimedia Commons or Wikipedia image page."
                    )
                    
                    print("\nExtracted data:")
                    for k, v in data.items():
                        if v:
                            print(f"  {k}: {v}")
            else:
                print("No images found on page")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    await browser.stop()


async def test_manar_direct():
    """Test Manar al-Athar with a direct link."""
    
    # A specific item page
    test_url = "https://www.manar-al-athar.ox.ac.uk/pages/view.php?ref=38453"
    
    client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))
    browser = StealthBrowserManager(headless=False)
    extractor = VisionBasedExtractor(client)
    verifier = ImageVerifier(client)
    
    print("\n\nTEST: Manar al-Athar Direct Image Page")
    print("=" * 60)
    
    await browser.start()
    
    try:
        async with browser.new_page() as page:
            print(f"Loading: {test_url}")
            await page.goto(test_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            # Take screenshot
            await page.screenshot(path="screenshots/manar_direct.png")
            
            # Check page type
            is_image_page = await verifier.verify_page(page)
            print(f"Is image detail page: {is_image_page}")
            
            if is_image_page:
                print("\nExtracting data...")
                data = await extractor.extract_with_vision(
                    page,
                    ArchiveRecord,
                    "Extract all metadata for this archaeological/historical image from the Manar al-Athar archive"
                )
                
                print("\nExtracted data:")
                filled_count = 0
                for k, v in data.items():
                    if v:
                        print(f"  {k}: {v}")
                        filled_count += 1
                
                print(f"\nFields filled: {filled_count}/23")
            else:
                print("Not recognized as image page. Taking debug screenshot...")
                await page.screenshot(path="screenshots/manar_debug.png")
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
    await browser.stop()


async def main():
    """Run tests."""
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set!")
        return
    
    print("REAL PAGE EXTRACTION TESTS")
    print("==========================\n")
    
    # Test different approaches
    await test_real_page()
    await test_manar_direct()
    
    print("\n\nTESTS COMPLETE!")


if __name__ == "__main__":
    asyncio.run(main())