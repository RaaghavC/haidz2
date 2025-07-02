#!/usr/bin/env python3
"""
Test script for Historical Architecture in Disaster Zones
Tests the TRUE AI brain with sites affected by the 2023 Turkey-Syria earthquake
Documents the process with screenshots using Puppeteer
"""

import asyncio
import os
import logging
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Import our AI brain
from src.agent.true_ai_brain import TrueAIBrain

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Historical sites affected by 2023 Turkey-Syria earthquake
EARTHQUAKE_SITES = [
    {
        "name": "Habib-i Neccar Mosque",
        "location": "Antakya",
        "description": "One of the oldest mosques in Anatolia, severely damaged",
        "search_terms": ["habib-i neccar mosque", "habib neccar camii", "antakya mosque"]
    },
    {
        "name": "Gaziantep Castle",
        "location": "Gaziantep",
        "description": "2nd millennium BC Hittite fortress, walls collapsed",
        "search_terms": ["gaziantep castle", "gaziantep kalesi", "gaziantep fortress"]
    },
    {
        "name": "Aleppo Citadel",
        "location": "Aleppo, Syria",
        "description": "Ottoman mill collapsed, defensive walls cracked",
        "search_terms": ["aleppo citadel", "halab castle", "حلب قلعة"]
    },
    {
        "name": "Antakya Synagogue",
        "location": "Antakya",
        "description": "Built in 1890, destroyed in earthquake",
        "search_terms": ["antakya synagogue", "antioch synagogue"]
    },
    {
        "name": "St Peter and Paul Church",
        "location": "Antakya",
        "description": "Orthodox church, heavily damaged",
        "search_terms": ["st peter paul church antakya", "orthodox church antioch"]
    }
]

# Archives to test
ARCHIVES_TO_TEST = [
    "https://www.archnet.org",
    "https://commons.wikimedia.org",
    "https://www.manar-al-athar.ox.ac.uk"
]


async def take_screenshot(page, filename, description):
    """Take a screenshot and log it"""
    screenshot_path = f"disaster_zones_{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    await page.screenshot(path=screenshot_path, full_page=True)
    logger.info(f"📸 Screenshot saved: {screenshot_path} - {description}")
    return screenshot_path


async def test_ai_brain_analysis(url, site_name):
    """Test the AI brain's analysis of an archive for a specific site"""
    logger.info(f"\n{'='*60}")
    logger.info(f"🧠 Testing AI Brain Analysis")
    logger.info(f"Archive: {url}")
    logger.info(f"Looking for: {site_name}")
    logger.info("="*60)
    
    try:
        # Initialize AI brain
        brain = TrueAIBrain()
        
        # Analyze the archive
        analysis = await brain.analyze_archive_with_ai(url)
        
        logger.info(f"\n📊 AI Analysis Results:")
        logger.info(f"Archive Type: {analysis.archive_type}")
        logger.info(f"Confidence: {analysis.confidence:.1%}")
        logger.info(f"Strategy: {analysis.recommended_strategy}")
        logger.info(f"Reasoning: {analysis.reasoning}")
        
        if analysis.extraction_hints:
            logger.info(f"\n🔍 Extraction Hints:")
            for key, value in analysis.extraction_hints.items():
                logger.info(f"  {key}: {value}")
        
        return analysis
        
    except Exception as e:
        logger.error(f"❌ AI analysis failed: {e}")
        return None


async def search_and_extract(brain, archive_url, search_query, max_results=5):
    """Search for a specific query in an archive"""
    logger.info(f"\n🔍 Searching for: '{search_query}'")
    
    try:
        results = await brain.scrape_intelligently(
            url=archive_url,
            search_query=search_query,
            output_file=f"disaster_zones_{search_query.replace(' ', '_')}.csv",
            max_results=max_results
        )
        
        logger.info(f"✅ Found {len(results)} results")
        
        # Display sample results
        if results:
            logger.info("\n📋 Sample Results:")
            for i, result in enumerate(results[:3]):
                logger.info(f"\n  Result {i+1}:")
                logger.info(f"    Title: {result.title}")
                logger.info(f"    Location: {result.orig_location}")
                logger.info(f"    Collection: {result.collection}")
                if result.notes:
                    logger.info(f"    Notes: {result.notes[:100]}...")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        return []


async def document_with_puppeteer(archive_url, site_info):
    """Use Puppeteer to document the search process"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser for demo
        page = await browser.new_page()
        
        try:
            # Navigate to archive
            logger.info(f"\n🌐 Navigating to {archive_url}")
            await page.goto(archive_url)
            await page.wait_for_load_state('networkidle')
            
            # Take initial screenshot
            await take_screenshot(page, "01_homepage", f"{archive_url} homepage")
            
            # Look for search functionality
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="search" i]',
                'input[placeholder*="ara" i]',  # Turkish for search
                'input[name*="search" i]',
                'input[name="q"]',
                '#search',
                '.search-input'
            ]
            
            search_found = False
            for selector in search_selectors:
                try:
                    search_input = await page.wait_for_selector(selector, timeout=3000)
                    if search_input:
                        logger.info(f"✅ Found search input: {selector}")
                        
                        # Type search query
                        await search_input.fill(site_info["search_terms"][0])
                        await take_screenshot(page, "02_search_typed", f"Typed: {site_info['search_terms'][0]}")
                        
                        # Submit search
                        await search_input.press('Enter')
                        await page.wait_for_load_state('networkidle')
                        await asyncio.sleep(2)
                        
                        await take_screenshot(page, "03_search_results", f"Search results for {site_info['name']}")
                        search_found = True
                        break
                except:
                    continue
            
            if not search_found:
                logger.warning("⚠️  No search functionality found")
                
                # Try direct navigation for ArchNet
                if "archnet.org" in archive_url:
                    sites_url = f"{archive_url}/sites"
                    logger.info(f"📍 Trying direct navigation to {sites_url}")
                    await page.goto(sites_url)
                    await page.wait_for_load_state('networkidle')
                    await take_screenshot(page, "04_sites_page", "ArchNet sites listing")
            
            # Look for relevant content
            content_text = await page.content()
            if any(term.lower() in content_text.lower() for term in site_info["search_terms"]):
                logger.info(f"✅ Found references to {site_info['name']}")
            else:
                logger.info(f"❓ No direct references found to {site_info['name']}")
                
        except Exception as e:
            logger.error(f"❌ Puppeteer error: {e}")
        finally:
            await browser.close()


async def main():
    """Main test function"""
    logger.info("\n" + "="*80)
    logger.info("🏛️  HISTORICAL ARCHITECTURE IN DISASTER ZONES TEST")
    logger.info("Testing TRUE AI Brain with 2023 Turkey-Syria Earthquake Sites")
    logger.info("="*80)
    
    # Check API key
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("❌ OPENAI_API_KEY not set in .env file")
        return
    
    # Initialize AI brain
    try:
        brain = TrueAIBrain()
        logger.info("✅ AI Brain initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize AI Brain: {e}")
        return
    
    # Test each archive with earthquake sites
    for archive_url in ARCHIVES_TO_TEST:
        logger.info(f"\n\n{'#'*80}")
        logger.info(f"📚 TESTING ARCHIVE: {archive_url}")
        logger.info("#"*80)
        
        # First, analyze the archive with AI
        analysis = await test_ai_brain_analysis(archive_url, "earthquake damaged sites")
        
        if not analysis:
            continue
        
        # Test with each earthquake site
        for site in EARTHQUAKE_SITES[:2]:  # Test first 2 sites to save time
            logger.info(f"\n\n{'+'*60}")
            logger.info(f"🏛️  SITE: {site['name']} ({site['location']})")
            logger.info(f"📝 {site['description']}")
            logger.info("+"*60)
            
            # Document with Puppeteer
            await document_with_puppeteer(archive_url, site)
            
            # Search and extract with AI brain
            for search_term in site["search_terms"][:1]:  # Use first search term
                results = await search_and_extract(brain, archive_url, search_term, max_results=3)
                
                if results:
                    logger.info(f"✅ Successfully extracted data for {site['name']}")
                else:
                    logger.info(f"❓ No results found for {site['name']} with term '{search_term}'")
            
            # Brief pause between sites
            await asyncio.sleep(2)
    
    logger.info("\n\n" + "="*80)
    logger.info("✅ TEST COMPLETE")
    logger.info("Check the generated CSV files and screenshots for results")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())