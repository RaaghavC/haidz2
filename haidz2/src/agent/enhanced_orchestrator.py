"""
Enhanced orchestrator for real-world archive scraping.
"""

import asyncio
from typing import List, Dict, Any, Optional
from playwright.async_api import Page
from datetime import datetime

from src.agent.config import AgentConfig
from src.models.schemas import ArchiveRecord, DataSchema
from src.models.strategies import VerificationResult
from src.modules.enhanced_analyzer import EnhancedAnalyzer
from src.modules.planner import Planner
from src.modules.enhanced_executor import EnhancedExecutor
from src.modules.verifier import Verifier
from src.modules.data_handler import DataHandler
from src.utils.browser_manager import BrowserManager
from src.strategies.archive_patterns import get_pattern_for_url


class EnhancedAutonomousScrapingAgent:
    """Enhanced autonomous agent for real-world archive scraping."""
    
    def __init__(self, target_url: str, config: AgentConfig):
        """Initialize the enhanced agent."""
        self.target_url = target_url
        self.config = config
        self.archive_pattern = get_pattern_for_url(target_url)
        
        # Initialize components
        self.browser_manager = BrowserManager()
        self.analyzer = EnhancedAnalyzer()
        self.planner = Planner()
        self.executor = EnhancedExecutor()
        self.verifier = Verifier()
        self.data_handler = DataHandler()
        self.schema = DataSchema()
        
        # State tracking
        self.all_data = []
        self.correction_attempts = 0
        
        print(f"\n{'='*60}")
        print(f"Enhanced Historical Architecture Scraper")
        print(f"{'='*60}")
        print(f"Target: {target_url}")
        if self.archive_pattern:
            print(f"Archive Type: {self.archive_pattern.name}")
            print(f"JavaScript Required: {self.archive_pattern.javascript_required}")
        print(f"{'='*60}\n")
    
    async def run(self) -> None:
        """Run the enhanced autonomous scraping agent."""
        start_time = datetime.now()
        
        try:
            # Start browser
            await self.browser_manager.start({"headless": self.config.headless})
            
            # Create page context
            async with self.browser_manager.create_page() as page:
                # Run cognitive loop
                await self._cognitive_loop(page)
            
            # Save final data
            self._save_data()
            
            # Print summary
            duration = (datetime.now() - start_time).total_seconds()
            print(f"\n{'='*60}")
            print(f"Scraping Complete")
            print(f"{'='*60}")
            print(f"Total Records: {len(self.all_data)}")
            print(f"Duration: {duration:.1f} seconds")
            print(f"Output: {self.config.output_file}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\n❌ Critical error: {e}")
            import traceback
            traceback.print_exc()
            
            # Save any collected data
            if self.all_data:
                self._save_data()
                print(f"Saved {len(self.all_data)} records before error")
            
        finally:
            await self.browser_manager.stop()
    
    async def _cognitive_loop(self, page: Page) -> None:
        """
        Main cognitive loop: Analyze → Plan → Execute → Verify → Self-correct
        """
# Removed hardcoded extraction - use autonomous approach for all archives
        
        # Navigate to target URL
        await self._navigate_to_target(page)
        
        while self.correction_attempts <= self.config.max_correction_attempts:
            print(f"\n{'='*50}")
            print(f"Cognitive Loop Iteration {self.correction_attempts + 1}")
            print(f"{'='*50}")
            
            # Phase 1: Analyze
            print("\n📊 Phase 1: Analyzing page structure...")
            analysis_result = await self._analysis_phase(page)
            
            if not analysis_result or analysis_result.confidence < 0.3:
                print("⚠️  Low confidence analysis, trying alternative approach...")
                # Try navigating to a collection or search page
                if await self._try_find_collection_page(page):
                    analysis_result = await self._analysis_phase(page)
            
            # Phase 2: Plan
            print("\n📋 Phase 2: Planning scraping strategy...")
            strategy = self._planning_phase(analysis_result)
            
            # Phase 3: Execute
            print("\n⚙️  Phase 3: Executing scraping strategy...")
            new_data = await self._execution_phase(strategy, page)
            
            if new_data:
                self.all_data.extend(new_data)
                print(f"✅ Collected {len(new_data)} new records (Total: {len(self.all_data)})")
            
            # Phase 4: Verify
            print("\n🔍 Phase 4: Verifying extracted data...")
            verification_result = self._verification_phase(self.all_data)
            
            # Check if we should continue
            if verification_result.is_valid or not self.config.enable_self_correction:
                print("✅ Data validation passed")
                break
            
            # Phase 5: Self-correct
            if self.correction_attempts < self.config.max_correction_attempts:
                print("\n🔄 Phase 5: Self-correction...")
                await self._self_correct(verification_result, page)
                self.correction_attempts += 1
            else:
                print("\n⚠️  Max correction attempts reached")
                break
            
            # Save intermediate results
            if self.config.save_intermediate and self.all_data:
                self._save_data()
    
    async def _navigate_to_target(self, page: Page) -> None:
        """Navigate to the target URL with enhanced error handling."""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                print(f"Navigating to {self.target_url}...")
                
                response = await page.goto(
                    self.target_url, 
                    wait_until="domcontentloaded",
                    timeout=90000
                )
                
                # Check response
                if response and response.status >= 400:
                    print(f"⚠️  HTTP {response.status} response")
                    
                    # Try alternative URLs for known patterns
                    if self.archive_pattern and attempt < max_attempts - 1:
                        alt_url = self._get_alternative_url()
                        if alt_url:
                            print(f"Trying alternative URL: {alt_url}")
                            self.target_url = alt_url
                            continue
                
                # Wait for JavaScript if detected or if archive pattern indicates it
                if self.archive_pattern and self.archive_pattern.javascript_required:
                    print("Waiting for JavaScript to render...")
                    # Try networkidle first, fallback to timeout on heavy sites
                    try:
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        print("Page reached network idle state")
                    except Exception:
                        print("Network idle timeout, using fixed wait instead...")
                        await page.wait_for_timeout(8000)
                else:
                    # Check for JavaScript frameworks dynamically
                    await page.wait_for_timeout(1000)  # Brief wait to let initial JS load
                    has_js_frameworks = await page.evaluate("""
                        () => {
                            return !!(window.React || window.Vue || window.Angular || 
                                    window.__NEXT_DATA__ || window.nuxt ||
                                    document.querySelector('[data-reactroot]') ||
                                    document.querySelector('[data-vue]'));
                        }
                    """)
                    
                    if has_js_frameworks:
                        print("Detected JavaScript framework, waiting for content...")
                        try:
                            await page.wait_for_load_state("networkidle", timeout=10000)
                        except Exception:
                            await page.wait_for_timeout(5000)
                
                await page.wait_for_timeout(2000)
                
                # Take screenshot of loaded page
                await page.screenshot(path="target_loaded.png")
                print("✅ Navigation successful")
                
                # Handle pre-navigation if required
                if self.archive_pattern and self.archive_pattern.pre_navigation_required:
                    print("Performing pre-navigation steps...")
                    await self._handle_pre_navigation(page)
                    print("✅ Pre-navigation completed")
                
                return
                
            except Exception as e:
                print(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(5)
                else:
                    raise
    
    async def _try_find_collection_page(self, page: Page) -> bool:
        """Try to navigate to a collection or search page."""
        print("Looking for collection/search pages...")
        
        # Common collection link patterns
        link_texts = [
            "Collections", "Browse", "Search", "Archive", "Gallery",
            "Photographs", "Images", "Media", "Database", "Catalog"
        ]
        
        for text in link_texts:
            try:
                # Try exact text
                link = await page.query_selector(f"a:has-text('{text}')")
                if not link:
                    # Try contains
                    link = await page.query_selector(f"a:has-text('{text.lower()}')")
                
                if link:
                    href = await link.get_attribute("href")
                    print(f"Found link: {text} -> {href}")
                    
                    await link.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000)
                    
                    # Check if we're on a listing page now
                    items = await page.query_selector_all("[class*='item'], [class*='result'], [class*='collection']")
                    if len(items) > 3:
                        print(f"✅ Navigated to collection page via '{text}' link")
                        return True
                        
            except Exception as e:
                print(f"Error trying link '{text}': {e}")
                continue
        
        return False
    
    def _get_alternative_url(self) -> Optional[str]:
        """Get alternative URL based on archive pattern."""
        base_url = self.target_url.rstrip('/')
        
        if "archnet.org" in base_url:
            if not base_url.endswith("/collections"):
                return f"{base_url}/collections"
        elif "manar-al-athar" in base_url:
            if "collections" not in base_url:
                return base_url.replace("pages/", "pages/collections_featured.php")
        
        return None
    
    async def _analysis_phase(self, page: Page) -> Any:
        """Enhanced analysis phase."""
        try:
            analysis_result = await self.analyzer.analyze_page(page)
            
            # Log analysis results
            print(f"  - Page type: {analysis_result.page_type}")
            print(f"  - Confidence: {analysis_result.confidence:.2f}")
            print(f"  - Element patterns: {len(analysis_result.element_patterns)}")
            print(f"  - Data containers: {len(analysis_result.data_containers)}")
            
            if analysis_result.data_containers:
                container = analysis_result.data_containers[0]
                print(f"  - Best container: {container.selector} -> {container.item_selector}")
                print(f"  - Sample fields: {list(container.sample_data[0].keys()) if container.sample_data else 'None'}")
            
            return analysis_result
            
        except Exception as e:
            print(f"❌ Analysis error: {e}")
            return None
    
    def _planning_phase(self, analysis_result) -> Any:
        """Enhanced planning phase."""
        try:
            strategy = self.planner.generate_strategy(analysis_result, self.schema)
            
            print(f"  - Container: {strategy.container_selector}")
            print(f"  - Items: {strategy.item_selector}")
            print(f"  - Navigation: {strategy.navigation_strategy.method}")
            print(f"  - Field mappings: {len(strategy.field_mapping.mappings)}")
            
            return strategy
            
        except Exception as e:
            print(f"❌ Planning error: {e}")
            return None
    
    async def _execution_phase(self, strategy, page: Page) -> List[Dict[str, Any]]:
        """Enhanced execution phase."""
        try:
            # Limit pages for initial testing
            if hasattr(strategy.navigation_strategy.parameters, 'max_pages'):
                strategy.navigation_strategy.parameters['max_pages'] = min(
                    strategy.navigation_strategy.parameters.get('max_pages', 100),
                    self.config.max_pages
                )
            else:
                strategy.navigation_strategy.parameters = {'max_pages': self.config.max_pages}
            
            data = await self.executor.execute_strategy(strategy, page)
            return data
            
        except Exception as e:
            print(f"❌ Execution error: {e}")
            return []
    
    def _verification_phase(self, data: List[Dict[str, Any]]) -> VerificationResult:
        """Enhanced verification phase."""
        result = self.verifier.verify_data(data, self.schema)
        
        if result.error_messages:
            print(f"  - Issues: {', '.join(result.error_messages[:3])}")
        
        print(f"  - Completeness: {result.completeness_score:.1%}")
        print(f"  - Quality: {result.quality_score:.1%}")
        
        return result
    
    async def _self_correct(self, verification_result: VerificationResult, page: Page) -> None:
        """Self-correction based on verification feedback."""
        print(f"  - Missing fields: {', '.join(verification_result.missing_fields)}")
        print(f"  - Recommendations: {', '.join(verification_result.recommendations[:2])}")
        
        # Take screenshot for debugging
        await page.screenshot(path=f"self_correct_{self.correction_attempts}.png")
        
        # In a more advanced implementation, this would:
        # 1. Analyze why fields are missing
        # 2. Try alternative selectors
        # 3. Navigate to detail pages
        # 4. Adjust extraction strategies
        
        await asyncio.sleep(2)
    
    def _save_data(self) -> None:
        """Save collected data to CSV."""
        if not self.all_data:
            print("No data to save")
            return
        
        try:
            # Convert to ArchiveRecord objects
            records = []
            for data_dict in self.all_data:
                try:
                    # Clean up data dict
                    cleaned_dict = {}
                    for key, value in data_dict.items():
                        if value is not None and str(value).strip():
                            cleaned_dict[key] = str(value).strip()
                    
                    record = ArchiveRecord(**cleaned_dict)
                    records.append(record)
                except Exception as e:
                    print(f"Skipping invalid record: {e}")
                    continue
            
            # Save to CSV
            if records:
                self.data_handler.save_to_csv(records, self.config.output_file)
                print(f"✅ Saved {len(records)} records to {self.config.output_file}")
            else:
                print("No valid records to save")
                
        except Exception as e:
            print(f"❌ Error saving data: {e}")
            
            # Save raw data as JSON fallback
            import json
            fallback_file = self.config.output_file.replace('.csv', '_raw.json')
            with open(fallback_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Raw data saved to {fallback_file}")
    
    async def _handle_pre_navigation(self, page: Page) -> None:
        """Handle pre-navigation steps required before data appears."""
        if not self.archive_pattern or not self.archive_pattern.pre_navigation_steps:
            return
        
        for step in self.archive_pattern.pre_navigation_steps:
            action = step.get("action")
            
            if action == "select":
                selector = step.get("selector")
                value = step.get("value")
                wait_after = step.get("wait_after", 1000)
                
                print(f"  - Selecting {value} in {selector}")
                try:
                    await page.select_option(selector, value)
                    await page.wait_for_timeout(wait_after)
                except Exception as e:
                    print(f"    ❌ Error in select action: {e}")
            
            elif action == "click":
                selector = step.get("selector")
                wait_after = step.get("wait_after", 1000)
                
                print(f"  - Clicking {selector}")
                try:
                    await page.click(selector)
                    await page.wait_for_timeout(wait_after)
                except Exception as e:
                    print(f"    ❌ Error in click action: {e}")
            
            elif action == "wait":
                timeout = step.get("timeout", 1000)
                await page.wait_for_timeout(timeout)
            
            elif action == "navigate_to_data":
                target_url = step.get("target_url")
                wait_after = step.get("wait_after", 3000)
                
                print(f"  - Navigating to data page: {target_url}")
                try:
                    # Build full URL
                    current_url = page.url
                    from urllib.parse import urljoin
                    full_url = urljoin(current_url, target_url)
                    
                    await page.goto(full_url, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(wait_after)
                    print(f"    ✅ Navigated to: {full_url}")
                except Exception as e:
                    print(f"    ❌ Error navigating to data page: {e}")
        
        # Wait for content to stabilize
        await page.wait_for_load_state("domcontentloaded")
    
# Removed direct extraction loop - using pure autonomous approach