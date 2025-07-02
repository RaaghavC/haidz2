#!/usr/bin/env python3
"""Debug ArchNet full workflow to find timeout point."""

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
from src.strategies.archive_patterns import get_pattern_for_url

async def debug_full_workflow():
    """Debug the full autonomous workflow step by step."""
    url = "https://www.archnet.org/"
    
    browser_manager = BrowserManager()
    analyzer = EnhancedAnalyzer()
    planner = Planner()
    executor = EnhancedExecutor()
    schema = DataSchema()
    
    try:
        print("🔍 Step 1: Starting browser...")
        await browser_manager.start({"headless": False})
        
        async with browser_manager.create_page() as page:
            print("🔍 Step 2: Navigation and wait...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(8000)  # Wait for JS
            await page.screenshot(path="debug_full_01_loaded.png")
            
            print("🔍 Step 3: Analysis phase...")
            analysis_result = await analyzer.analyze_page(page)
            print(f"   Analysis confidence: {analysis_result.confidence}")
            print(f"   Data containers found: {len(analysis_result.data_containers)}")
            
            if analysis_result.data_containers:
                container = analysis_result.data_containers[0]
                print(f"   Best container: {container.selector} -> {container.item_selector}")
                await page.screenshot(path="debug_full_02_analyzed.png")
            
            print("🔍 Step 4: Planning phase...")
            try:
                strategy = planner.generate_strategy(analysis_result, schema)
                print(f"   Strategy created successfully")
                print(f"   Container: {strategy.container_selector}")
                print(f"   Item selector: {strategy.item_selector}")
                print(f"   Navigation method: {strategy.navigation_strategy.method}")
                print(f"   Field mappings: {len(strategy.field_mapping.mappings)}")
                
                # Show some field mappings
                if strategy.field_mapping.mappings:
                    print("   Sample mappings:")
                    for field, selector in list(strategy.field_mapping.mappings.items())[:3]:
                        print(f"     {field}: {selector}")
                
            except Exception as e:
                print(f"   Planning failed: {e}")
                import traceback
                traceback.print_exc()
                return
            
            print("🔍 Step 5: Execution phase (limited to 5 items)...")
            try:
                # Limit to prevent timeout
                original_params = strategy.navigation_strategy.parameters
                strategy.navigation_strategy.parameters = {"max_pages": 1, "max_items": 5}
                
                print("   Starting extraction...")
                data = await executor.execute_strategy(strategy, page)
                print(f"   Extracted {len(data)} items")
                
                if data:
                    print("   Sample data:")
                    for i, item in enumerate(data[:2]):
                        print(f"   Item {i+1}: {item}")
                
                await page.screenshot(path="debug_full_03_extracted.png")
                
            except Exception as e:
                print(f"   Execution failed: {e}")
                import traceback
                traceback.print_exc()
                await page.screenshot(path="debug_full_03_execution_failed.png")
            
            print("🔍 Debug workflow complete!")
            
    except Exception as e:
        print(f"❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser_manager.stop()

if __name__ == "__main__":
    asyncio.run(debug_full_workflow())