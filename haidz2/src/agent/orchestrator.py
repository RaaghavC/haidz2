"""Main orchestrator for the autonomous scraping agent."""

import asyncio
from typing import List, Dict, Any, Optional
from playwright.async_api import Page

from src.agent.config import AgentConfig
from src.modules.analyzer import Analyzer
from src.modules.planner import Planner
from src.modules.executor import Executor
from src.modules.verifier import Verifier
from src.modules.data_handler import DataHandler
from src.models.schemas import DataSchema, ArchiveRecord
from src.models.strategies import AnalysisResult, ScrapingStrategy, VerificationResult
from src.utils.browser_manager import BrowserManager


class AutonomousScrapingAgent:
    """
    Main orchestrator implementing the cognitive loop.
    
    The agent follows: Analyze → Plan → Execute → Verify → (Self-correct if needed)
    """
    
    def __init__(self, target_url: str, config: Optional[AgentConfig] = None):
        """
        Initialize the autonomous agent.
        
        Args:
            target_url: URL of the archive to scrape
            config: Agent configuration
        """
        self.target_url = target_url
        self.config = config or AgentConfig()
        
        # Initialize modules
        self.analyzer = Analyzer()
        self.planner = Planner()
        self.executor = Executor()
        self.verifier = Verifier()
        self.data_handler = DataHandler()
        
        # Schema
        self.schema = DataSchema()
        
        # State tracking
        self.correction_attempts = 0
        self.all_data: List[Dict[str, Any]] = []
    
    async def run(self) -> None:
        """
        Execute the autonomous scraping agent.
        
        This is the main entry point that orchestrates the cognitive loop.
        """
        try:
            print(f"Starting autonomous scraping of {self.target_url}")
            
            # Create browser manager
            browser_manager = BrowserManager()
            
            try:
                async with browser_manager.create_page() as page:
                    # Navigate to target URL
                    await page.goto(self.target_url)
                    
                    # Execute cognitive loop
                    await self._cognitive_loop(page)
                    
            finally:
                await browser_manager.stop()
            
            # Save final data
            self._save_data()
            
            print(f"Scraping completed. Data saved to {self.config.output_file}")
            
        except Exception as e:
            print(f"Critical error in agent: {e}")
            # Save whatever data we have
            self._save_data()
    
    async def _cognitive_loop(self, page: Page) -> None:
        """
        Execute the main cognitive loop.
        
        Args:
            page: Playwright page object
        """
        while self.correction_attempts <= self.config.max_correction_attempts:
            try:
                # Phase 1: Analyze
                print("Phase 1: Analyzing page structure...")
                analysis_result = await self._analyze_phase(page)
                
                if analysis_result.confidence < 0.5:
                    print("Low confidence in analysis. Attempting different approach...")
                    self.correction_attempts += 1
                    continue
                
                # Phase 2: Plan
                print("Phase 2: Planning scraping strategy...")
                strategy = self._planning_phase(analysis_result)
                
                # Phase 3: Execute
                print("Phase 3: Executing scraping strategy...")
                scraped_data = await self._execution_phase(strategy)
                
                # Phase 4: Verify
                print("Phase 4: Verifying extracted data...")
                verification_result = self._verification_phase(scraped_data)
                
                # Check if self-correction is needed
                if not verification_result.is_valid and self.config.enable_self_correction:
                    print("Data validation failed. Attempting self-correction...")
                    print(f"Issues: {', '.join(verification_result.error_messages)}")
                    print(f"Recommendations: {', '.join(verification_result.recommendations)}")
                    
                    self.correction_attempts += 1
                    
                    # Adjust strategy based on recommendations
                    await self._self_correct(verification_result)
                    continue
                
                # Success - add data to collection
                self.all_data.extend(scraped_data)
                
                # Save intermediate results if configured
                if self.config.save_intermediate:
                    self._save_data()
                
                # Exit loop on success
                break
                
            except Exception as e:
                print(f"Error in cognitive loop: {e}")
                self.correction_attempts += 1
                
                if self.correction_attempts > self.config.max_correction_attempts:
                    print("Max correction attempts reached. Saving partial data...")
                    break
    
    async def _analyze_phase(self, page: Page) -> AnalysisResult:
        """
        Analyze the current page structure.
        
        Args:
            page: Playwright page object
            
        Returns:
            Analysis result
        """
        return await self.analyzer.analyze_page(page)
    
    def _planning_phase(self, analysis: AnalysisResult) -> ScrapingStrategy:
        """
        Generate scraping strategy from analysis.
        
        Args:
            analysis: Page analysis result
            
        Returns:
            Scraping strategy
        """
        return self.planner.generate_strategy(analysis, self.schema)
    
    async def _execution_phase(self, strategy: ScrapingStrategy) -> List[Dict[str, Any]]:
        """
        Execute the scraping strategy.
        
        Args:
            strategy: Scraping strategy to execute
            
        Returns:
            List of scraped records
        """
        # Use separate executor instance with its own browser
        executor = Executor()
        return await executor.execute_strategy(strategy)
    
    def _verification_phase(self, data: List[Dict[str, Any]]) -> VerificationResult:
        """
        Verify the quality of scraped data.
        
        Args:
            data: Scraped data records
            
        Returns:
            Verification result
        """
        return self.verifier.verify_data(data, self.schema)
    
    async def _self_correct(self, verification_result: VerificationResult) -> None:
        """
        Attempt to self-correct based on verification feedback.
        
        Args:
            verification_result: Result from verification phase
        """
        # Log the issues for learning
        print("\nSelf-correction analysis:")
        print(f"- Completeness: {verification_result.completeness_score:.1%}")
        print(f"- Quality: {verification_result.quality_score:.1%}")
        print(f"- Missing fields: {', '.join(verification_result.missing_fields)}")
        print(f"- Invalid records: {len(verification_result.invalid_records)}")
        
        # In a more advanced implementation, this would:
        # 1. Analyze why fields are missing
        # 2. Adjust selector patterns
        # 3. Try alternative extraction methods
        # 4. Look for data in different page areas
        
        # For now, we'll retry with the existing approach
        await asyncio.sleep(2)  # Brief pause before retry
    
    def _save_data(self) -> None:
        """Save collected data to CSV."""
        try:
            # Convert to ArchiveRecord objects
            records = []
            for data_dict in self.all_data:
                try:
                    # Debug: print the first record's keys
                    if len(records) == 0 and self.config.log_level == "DEBUG":
                        print(f"Data dict keys: {list(data_dict.keys())}")
                        print(f"Sample values: Title='{data_dict.get('Title')}', Typ='{data_dict.get('Typ')}'")
                    
                    record = ArchiveRecord(**data_dict)
                    records.append(record)
                except Exception as e:
                    if self.config.log_level == "DEBUG":
                        print(f"Skipping invalid record: {e}")
                        print(f"Data was: {data_dict}")
                    continue
            
            # Save to CSV
            self.data_handler.save_to_csv(records, self.config.output_file)
            print(f"Saved {len(records)} records to {self.config.output_file}")
            
        except Exception as e:
            print(f"Error saving data: {e}")
            # Last resort - save raw data
            import json
            with open(self.config.output_file.replace('.csv', '.json'), 'w') as f:
                json.dump(self.all_data, f, indent=2)