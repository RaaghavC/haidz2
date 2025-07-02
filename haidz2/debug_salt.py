#!/usr/bin/env python3
"""Debug SALT Research autonomous workflow."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.browser_manager import BrowserManager
from src.modules.enhanced_analyzer import EnhancedAnalyzer
from src.modules.planner import Planner
from src.modules.enhanced_executor import EnhancedExecutor
from src.models.schemas import DataSchema

async def debug_salt():
    """Debug SALT Research autonomous workflow."""
    url = "https://saltresearch.org/discovery/search?vid=90GARANTI_INST:90SALT_VU1&lang=en"
    
    browser_manager = BrowserManager()
    analyzer = EnhancedAnalyzer()
    planner = Planner()
    executor = EnhancedExecutor()
    schema = DataSchema()
    
    try:
        print("🔍 Testing SALT Research...")
        await browser_manager.start({"headless": False})
        
        async with browser_manager.create_page() as page:
            print("🔍 Step 1: Navigation...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(8000)  # Wait for JS framework
            await page.screenshot(path="debug_salt_01_loaded.png")
            
            print("🔍 Step 2: Check for search functionality...")
            # Try to search for something to get results
            try:
                search_input = await page.query_selector("input[type='search'], input[placeholder*='Search'], #searchbox")
                if search_input:
                    await search_input.fill("photography")
                    
                    # Find and click search button
                    search_button = await page.query_selector("button[type='submit'], .search-button, button:has(svg)")
                    if search_button:
                        await search_button.click()
                        await page.wait_for_load_state("domcontentloaded")
                        await page.wait_for_timeout(5000)
                        await page.screenshot(path="debug_salt_02_search_results.png")
                        print("   Searched for 'photography'")
                    else:
                        print("   No search button found")
                else:
                    print("   No search input found")
            except Exception as e:
                print(f"   Search attempt failed: {e}")
            
            print("🔍 Step 3: Analysis...")
            analysis_result = await analyzer.analyze_page(page)
            print(f"   Analysis confidence: {analysis_result.confidence}")
            print(f"   Data containers found: {len(analysis_result.data_containers)}")
            
            if analysis_result.data_containers:
                container = analysis_result.data_containers[0]
                print(f"   Best container: {container.selector} -> {container.item_selector}")
            
            print("🔍 Step 4: Planning...")
            strategy = planner.generate_strategy(analysis_result, schema)
            print(f"   Strategy: {strategy.container_selector} -> {strategy.item_selector}")
            print(f"   Navigation: {strategy.navigation_strategy.method}")
            
            print("🔍 Step 5: Execution...")
            strategy.navigation_strategy.parameters = {"max_pages": 1, "max_items": 10}
            data = await executor.execute_strategy(strategy, page)
            print(f"   Extracted {len(data)} items")
            
            if data:
                print("   Sample data:")
                for i, item in enumerate(data[:2]):
                    print(f"   Item {i+1}: {item}")
            
            await page.screenshot(path="debug_salt_03_final.png")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser_manager.stop()

if __name__ == "__main__":
    asyncio.run(debug_salt())