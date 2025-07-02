#!/usr/bin/env python3
"""Debug Manar al-Athar autonomous workflow."""

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

async def debug_manar():
    """Debug Manar al-Athar autonomous workflow."""
    url = "https://www.manar-al-athar.ox.ac.uk/"
    
    browser_manager = BrowserManager()
    analyzer = EnhancedAnalyzer()
    planner = Planner()
    executor = EnhancedExecutor()
    schema = DataSchema()
    
    try:
        print("🔍 Testing Manar al-Athar...")
        await browser_manager.start({"headless": False})
        
        async with browser_manager.create_page() as page:
            print("🔍 Step 1: Navigation...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)
            await page.screenshot(path="debug_manar_01_loaded.png")
            
            # Navigate to a more data-rich page (search results)
            print("🔍 Step 2: Navigate to search page...")
            try:
                # Click on "Search Results" or similar
                search_link = await page.query_selector("a[href*='search']")
                if search_link:
                    await search_link.click()
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path="debug_manar_02_search_page.png")
                else:
                    print("   No search link found, continuing with homepage")
            except Exception as e:
                print(f"   Navigation to search failed: {e}")
            
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
            
            await page.screenshot(path="debug_manar_03_final.png")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser_manager.stop()

if __name__ == "__main__":
    asyncio.run(debug_manar())