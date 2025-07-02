#!/usr/bin/env python3
"""Debug ArchNet step by step to see where it's failing."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.browser_manager import BrowserManager
from src.modules.enhanced_analyzer import EnhancedAnalyzer
from src.strategies.archive_patterns import get_pattern_for_url, get_wait_strategy

async def debug_archnet():
    """Debug ArchNet navigation and analysis step by step."""
    url = "https://www.archnet.org/"
    
    browser_manager = BrowserManager()
    analyzer = EnhancedAnalyzer()
    
    try:
        print("🔍 Step 1: Starting browser...")
        await browser_manager.start({"headless": False})
        
        print("🔍 Step 2: Creating page...")
        async with browser_manager.create_page() as page:
            
            print("🔍 Step 3: Getting archive pattern...")
            archive_pattern = get_pattern_for_url(url)
            if archive_pattern:
                print(f"   Found pattern: {archive_pattern.name}")
                print(f"   JavaScript required: {archive_pattern.javascript_required}")
            
            print("🔍 Step 4: Navigating to ArchNet...")
            await page.screenshot(path="debug_01_before_navigation.png")
            
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                print(f"   Response status: {response.status if response else 'None'}")
                await page.screenshot(path="debug_02_after_goto.png")
            except Exception as e:
                print(f"   Navigation failed: {e}")
                await page.screenshot(path="debug_02_navigation_failed.png")
                return
            
            print("🔍 Step 5: Waiting for JavaScript...")
            try:
                # Check for JavaScript frameworks
                await page.wait_for_timeout(2000)
                await page.screenshot(path="debug_03_after_initial_wait.png")
                
                has_js = await page.evaluate("""
                    () => {
                        return {
                            hasReact: !!(window.React || document.querySelector('[data-reactroot]')),
                            hasNextData: !!window.__NEXT_DATA__,
                            hasVue: !!(window.Vue || document.querySelector('[data-vue]')),
                            hasAngular: !!window.Angular,
                            title: document.title,
                            url: window.location.href,
                            bodyChildCount: document.body ? document.body.children.length : 0
                        };
                    }
                """)
                print(f"   JS Framework detection: {has_js}")
                
                if has_js['hasReact'] or has_js['hasNextData']:
                    print("   Waiting for React/Next.js to load...")
                    try:
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        print("   Network idle reached")
                    except Exception:
                        print("   Network idle timeout, using fixed wait...")
                        await page.wait_for_timeout(8000)
                
                await page.screenshot(path="debug_04_after_js_wait.png")
                
            except Exception as e:
                print(f"   JavaScript wait failed: {e}")
                await page.screenshot(path="debug_04_js_wait_failed.png")
            
            print("🔍 Step 6: Checking page content...")
            page_info = await page.evaluate("""
                () => {
                    const body = document.body;
                    const content = {
                        title: document.title,
                        url: window.location.href,
                        bodyHTML: body ? body.innerHTML.substring(0, 500) + '...' : 'No body',
                        hasContent: body ? body.children.length > 0 : false,
                        visibleText: document.body ? document.body.innerText.substring(0, 200) + '...' : 'No text'
                    };
                    
                    // Look for common content indicators
                    const indicators = [
                        '.results', '.items', '[class*="grid"]', '[class*="card"]',
                        '[class*="result"]', '[class*="collection"]', 'article', 'main'
                    ];
                    
                    content.foundSelectors = [];
                    indicators.forEach(sel => {
                        const elements = document.querySelectorAll(sel);
                        if (elements.length > 0) {
                            content.foundSelectors.push(`${sel}: ${elements.length}`);
                        }
                    });
                    
                    return content;
                }
            """)
            
            print(f"   Page info: {page_info}")
            await page.screenshot(path="debug_05_page_content_check.png")
            
            print("🔍 Step 7: Running analyzer...")
            try:
                analysis_result = await analyzer.analyze_page(page)
                print(f"   Analysis confidence: {analysis_result.confidence}")
                print(f"   Page type: {analysis_result.page_type}")
                print(f"   Data containers found: {len(analysis_result.data_containers)}")
                print(f"   Element patterns found: {len(analysis_result.element_patterns)}")
                
                if analysis_result.data_containers:
                    container = analysis_result.data_containers[0]
                    print(f"   Best container: {container.selector} -> {container.item_selector}")
                    print(f"   Sample data: {container.sample_data[:1] if container.sample_data else 'None'}")
                
                await page.screenshot(path="debug_06_after_analysis.png")
                
            except Exception as e:
                print(f"   Analysis failed: {e}")
                import traceback
                traceback.print_exc()
                await page.screenshot(path="debug_06_analysis_failed.png")
            
            print("🔍 Debug complete. Check screenshots for details.")
            
    except Exception as e:
        print(f"❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser_manager.stop()

if __name__ == "__main__":
    asyncio.run(debug_archnet())