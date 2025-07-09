#!/usr/bin/env python3
"""
Test specific archives with known working URLs.
"""

import asyncio
import os
import sys
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agent.true_agentic_orchestrator import TrueAgenticOrchestrator
from src.agent.config import AgentConfig
from src.modules.vision_extractor import VisionBasedExtractor
from src.modules.image_verifier import ImageVerifier
from src.models.schemas import ArchiveRecord
from src.utils.stealth_browser_manager import StealthBrowserManager
import openai


async def test_nyu_akkasah():
    """Test NYU AD Akkasah Center page."""
    
    print("\n" + "="*70)
    print("TEST: NYU AD Akkasah Center")
    print("="*70)
    
    config = AgentConfig(
        output_file=f"csv/nyu_akkasah_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        max_results=2,
        max_pages=5,
        headless=False  # Show browser
    )
    
    orchestrator = TrueAgenticOrchestrator(
        target_url="https://nyuad.nyu.edu/en/research/faculty-labs-and-projects/akkasah-center-for-photography.html",
        search_query=None,  # No search on this page
        config=config,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    result = await orchestrator.run()
    
    print(f"\nResults:")
    print(f"  Success: {result['success']}")
    print(f"  Items extracted: {result['items_scraped']}")
    
    if result.get('error'):
        print(f"  Error: {result['error']}")
    
    return result


async def test_salt_research():
    """Test SALT Research with direct image URL."""
    
    print("\n" + "="*70)
    print("TEST: SALT Research - Direct Image Page")
    print("="*70)
    
    # Test with a direct image page if we can find one
    # This URL is a search results page, so the AI will need to navigate
    test_url = "https://saltresearch.org/discovery/search?vid=90GARANTI_INST:90SALT_VU1&lang=en"
    
    client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))
    browser = StealthBrowserManager(headless=False)
    extractor = VisionBasedExtractor(client)
    verifier = ImageVerifier(client)
    
    await browser.start()
    
    try:
        async with browser.new_page() as page:
            print(f"Loading: {test_url}")
            await page.goto(test_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            # Try to search for "Antakya"
            print("Searching for 'Antakya'...")
            search_input = await page.query_selector('input[type="search"], input[name="q"], input[placeholder*="search" i]')
            if search_input:
                await search_input.fill("Antakya")
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(5000)
                
                # Take screenshot of results
                await page.screenshot(path="screenshots/salt_search_results.png")
                print("Screenshot saved: screenshots/salt_search_results.png")
                
                # Check if it's showing results
                is_results = await verifier.verify_page(page)
                print(f"Is image detail page: {is_results}")
                
                if not is_results:
                    print("Attempting to click on first result...")
                    # Try to click on first result
                    first_result = await page.query_selector('a[href*="fulldisplay"]')
                    if first_result:
                        await first_result.click()
                        await page.wait_for_timeout(5000)
                        
                        # Check again
                        is_detail = await verifier.verify_page(page)
                        print(f"Is detail page now: {is_detail}")
                        
                        if is_detail:
                            # Extract data
                            data = await extractor.extract_with_vision(
                                page,
                                ArchiveRecord,
                                "Extract all metadata for this historical image"
                            )
                            
                            print("\nExtracted data:")
                            for k, v in data.items():
                                if v:
                                    print(f"  {k}: {v}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
    await browser.stop()


async def test_wikimedia():
    """Test Wikimedia Commons."""
    
    print("\n" + "="*70)
    print("TEST: Wikimedia Commons")
    print("="*70)
    
    # Direct image page on Wikimedia - using a real file
    test_url = "https://commons.wikimedia.org/wiki/File:Antakya_Habib_Neccar_Camii.jpg"
    
    client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))
    browser = StealthBrowserManager(headless=False)
    extractor = VisionBasedExtractor(client)
    verifier = ImageVerifier(client)
    
    await browser.start()
    
    try:
        async with browser.new_page() as page:
            print(f"Loading: {test_url}")
            await page.goto(test_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            # Take screenshot
            await page.screenshot(path="screenshots/wikimedia_test.png")
            
            # Verify page type
            is_image_page = await verifier.verify_page(page)
            print(f"Is image detail page: {is_image_page}")
            
            if is_image_page:
                # Extract data
                print("\nExtracting data...")
                data = await extractor.extract_with_vision(
                    page,
                    ArchiveRecord,
                    "Extract all available metadata for this historical image including title, date, location, photographer, description, and any other relevant information"
                )
                
                print("\nExtracted data:")
                for k, v in data.items():
                    if v:
                        print(f"  {k}: {v}")
                        
                # Calculate completeness
                filled = sum(1 for v in data.values() if v)
                total = len(data)
                print(f"\nCompleteness: {filled}/{total} ({filled/total*100:.1f}%)")
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
    await browser.stop()


async def main():
    """Run all tests."""
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set!")
        return
    
    print("SPECIFIC ARCHIVE TESTS")
    print("======================")
    print("Testing vision-based extraction on specific archives")
    
    # Test each archive
    # await test_nyu_akkasah()
    # await test_salt_research()
    await test_wikimedia()
    
    print("\n\nALL TESTS COMPLETE!")


if __name__ == "__main__":
    asyncio.run(main())