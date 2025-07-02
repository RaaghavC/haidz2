"""
True AI Brain for Autonomous Scraping Decision-Making
Uses LLM-powered reasoning for intelligent strategy selection and adaptation
Based on ReAct pattern and function calling for tool selection
"""

import asyncio
import json
import logging
from typing import Optional, List, Dict, Any, Type, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass
import openai
from tenacity import retry, stop_after_attempt, wait_exponential
import aiohttp
import ssl

from src.strategies.base_strategy import BaseExtractionStrategy
from src.strategies.archnet_strategy import ArchNetStrategy
from src.strategies.wikimedia_strategy import WikimediaStrategy
from src.strategies.manar_strategy import ManarStrategy
from src.strategies.browser_strategy import BrowserAutonomousStrategy
from src.strategies.api_detection_strategy import APIDetectionStrategy
from src.modules.data_handler import DataHandler

logger = logging.getLogger(__name__)


@dataclass
class ArchiveAnalysis:
    """Results from AI analysis of an archive"""
    url: str
    domain: str
    archive_type: str
    characteristics: Dict[str, Any]
    recommended_strategy: str
    confidence: float
    reasoning: str
    extraction_hints: Dict[str, Any]


class TrueAIBrain:
    """
    LLM-powered AI agent that uses reasoning and learning for intelligent
    archive analysis and strategy selection. Implements the ReAct pattern.
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize with OpenAI API key from environment or parameter"""
        import os
        from dotenv import load_dotenv
        
        # Load environment variables from .env file
        load_dotenv()
        
        self.api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
        
        openai.api_key = self.api_key
        self.client = openai.Client(api_key=self.api_key)
        
        # Available strategies
        self.strategies = {
            'ArchNetStrategy': ArchNetStrategy,
            'WikimediaStrategy': WikimediaStrategy,
            'ManarStrategy': ManarStrategy,
            'BrowserAutonomousStrategy': BrowserAutonomousStrategy,
            'APIDetectionStrategy': APIDetectionStrategy,
        }
        
        # Learning memory (in production, use vector DB)
        self.archive_patterns = []
        self.successful_extractions = []
        self.failed_attempts = []
        
        self.data_handler = DataHandler()
    
    def _create_analysis_prompt(self, url: str, page_content: str) -> str:
        """Create a comprehensive prompt for archive analysis"""
        return f"""You are an expert web scraping strategist analyzing a digital archive.
        
URL: {url}
Domain: {urlparse(url).netloc}

Page Content Sample (first 5000 chars):
{page_content[:5000]}

Analyze this archive and provide a detailed assessment following the ReAct pattern:

THOUGHT: Analyze the archive structure, technology stack, and data organization
ACTION: Determine the optimal extraction strategy
OBSERVATION: Identify specific patterns and extraction hints

Consider:
1. Technology Stack: Is it using React, Vue, Next.js, or server-rendered HTML?
2. API Availability: Are there exposed APIs (Algolia, GraphQL, REST)?
3. Data Structure: How is archival data organized (listings, galleries, search)?
4. Authentication: Does it require login or have public access?
5. JavaScript Rendering: Is content loaded dynamically?
6. Known Patterns: Does it match known archive types (IIIF, OAI-PMH, MediaWiki)?

Available Strategies:
- ArchNetStrategy: For ArchNet with Algolia API
- WikimediaStrategy: For MediaWiki-based sites
- ManarStrategy: For Manar al-Athar specific patterns
- APIDetectionStrategy: For sites with detectable APIs
- BrowserAutonomousStrategy: Universal browser-based extraction

Provide your analysis in this JSON format:
{{
    "archive_type": "academic|museum|library|media|unknown",
    "characteristics": {{
        "technology_stack": ["react", "nextjs", etc],
        "has_api": true/false,
        "api_type": "algolia|graphql|rest|none",
        "requires_js_rendering": true/false,
        "authentication_required": true/false,
        "data_format": "structured|semi-structured|unstructured",
        "iiif_compatible": true/false
    }},
    "recommended_strategy": "StrategyClassName",
    "confidence": 0.0-1.0,
    "reasoning": "Detailed explanation of why this strategy was chosen",
    "extraction_hints": {{
        "selectors": ["specific CSS selectors if found"],
        "api_endpoints": ["detected API endpoints"],
        "pagination_pattern": "description of pagination if found",
        "metadata_locations": ["where metadata is stored"]
    }}
}}"""
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API with retry logic"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in web scraping, digital archives, and extraction strategies."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,  # Lower temperature for more consistent analysis
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            # Fallback to basic analysis
            return {
                "archive_type": "unknown",
                "characteristics": {"requires_js_rendering": True},
                "recommended_strategy": "BrowserAutonomousStrategy",
                "confidence": 0.5,
                "reasoning": "LLM analysis failed, using universal browser strategy",
                "extraction_hints": {}
            }
    
    async def _fetch_page_content(self, url: str) -> str:
        """Fetch page content for analysis"""
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, ssl=ssl_context, timeout=10) as response:
                    return await response.text()
        except Exception as e:
            logger.warning(f"Failed to fetch page content: {e}")
            return ""
    
    async def analyze_archive_with_ai(self, url: str) -> ArchiveAnalysis:
        """
        Use LLM to intelligently analyze the archive and recommend strategy
        Implements the ReAct pattern for reasoning
        """
        logger.info(f"🧠 True AI Brain analyzing: {url}")
        
        # Step 1: Fetch page content
        page_content = await self._fetch_page_content(url)
        
        # Step 2: Create analysis prompt
        prompt = self._create_analysis_prompt(url, page_content)
        
        # Step 3: Get LLM analysis
        logger.info("🤔 AI reasoning about archive structure...")
        analysis_result = await self._call_llm(prompt)
        
        # Step 4: Create structured analysis
        analysis = ArchiveAnalysis(
            url=url,
            domain=urlparse(url).netloc,
            archive_type=analysis_result.get('archive_type', 'unknown'),
            characteristics=analysis_result.get('characteristics', {}),
            recommended_strategy=analysis_result.get('recommended_strategy', 'BrowserAutonomousStrategy'),
            confidence=analysis_result.get('confidence', 0.5),
            reasoning=analysis_result.get('reasoning', ''),
            extraction_hints=analysis_result.get('extraction_hints', {})
        )
        
        # Step 5: Learn from this analysis (store for future reference)
        self.archive_patterns.append({
            'domain': analysis.domain,
            'characteristics': analysis.characteristics,
            'strategy': analysis.recommended_strategy
        })
        
        logger.info(f"✅ AI Analysis Complete:")
        logger.info(f"  - Archive Type: {analysis.archive_type}")
        logger.info(f"  - Strategy: {analysis.recommended_strategy}")
        logger.info(f"  - Confidence: {analysis.confidence:.1%}")
        logger.info(f"  - Reasoning: {analysis.reasoning}")
        
        return analysis
    
    async def select_strategy_with_reasoning(
        self, 
        analysis: ArchiveAnalysis
    ) -> Tuple[BaseExtractionStrategy, Dict[str, Any]]:
        """
        Select and configure strategy based on AI analysis
        Returns strategy instance and configuration hints
        """
        strategy_class_name = analysis.recommended_strategy
        
        # Validate strategy exists
        if strategy_class_name not in self.strategies:
            logger.warning(f"Unknown strategy {strategy_class_name}, using browser fallback")
            strategy_class_name = 'BrowserAutonomousStrategy'
        
        # Instantiate strategy
        strategy_class = self.strategies[strategy_class_name]
        strategy = strategy_class()
        
        # Configure strategy with AI hints
        config = {
            'extraction_hints': analysis.extraction_hints,
            'archive_type': analysis.archive_type,
            'characteristics': analysis.characteristics
        }
        
        # If strategy supports configuration, apply it
        if hasattr(strategy, 'configure'):
            strategy.configure(config)
        
        return strategy, config
    
    async def learn_from_extraction(
        self, 
        url: str, 
        strategy_used: str, 
        results: List[Any], 
        success: bool
    ):
        """
        Learn from extraction results to improve future decisions
        In production, this would update a vector database
        """
        feedback = {
            'url': url,
            'domain': urlparse(url).netloc,
            'strategy': strategy_used,
            'result_count': len(results),
            'success': success,
            'timestamp': asyncio.get_event_loop().time()
        }
        
        if success:
            self.successful_extractions.append(feedback)
            logger.info(f"✅ Learned from successful extraction: {strategy_used} on {urlparse(url).netloc}")
        else:
            self.failed_attempts.append(feedback)
            logger.warning(f"❌ Learned from failed extraction: {strategy_used} on {urlparse(url).netloc}")
    
    async def scrape_intelligently(
        self, 
        url: str, 
        search_query: str = "",
        output_file: str = "scraped_data.csv",
        max_results: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Main entry point for intelligent scraping with true AI reasoning
        """
        logger.info("="*60)
        logger.info("🧠 TRUE AI-POWERED SCRAPING ENGINE")
        logger.info("="*60)
        
        # Phase 1: AI-Powered Analysis
        logger.info("\n📊 PHASE 1: AI Archive Analysis")
        analysis = await self.analyze_archive_with_ai(url)
        
        # Phase 2: Strategy Selection with Reasoning
        logger.info(f"\n⚙️  PHASE 2: Strategy Selection")
        strategy, config = await self.select_strategy_with_reasoning(analysis)
        logger.info(f"Selected: {strategy.__class__.__name__}")
        
        # Phase 3: Execute Extraction
        logger.info(f"\n🔍 PHASE 3: Intelligent Extraction")
        if search_query:
            logger.info(f"Search Filter: '{search_query}'")
        
        try:
            results = await strategy.extract(
                url=url,
                search_query=search_query,
                max_results=max_results
            )
            
            # Phase 4: Learn from Results
            success = len(results) > 0
            await self.learn_from_extraction(
                url, 
                strategy.__class__.__name__, 
                results, 
                success
            )
            
            # Phase 5: Save Results
            if results:
                logger.info(f"\n💾 PHASE 5: Saving Results")
                self.data_handler.save_to_csv(results, output_file)
                logger.info(f"Data saved to: {output_file}")
            else:
                logger.warning("No results found")
            
            return results
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            
            # Learn from failure
            await self.learn_from_extraction(
                url, 
                strategy.__class__.__name__, 
                [], 
                False
            )
            
            # Try adaptive fallback based on confidence
            if analysis.confidence < 0.8:
                logger.info("\n🔄 Attempting AI-suggested fallback...")
                
                # Ask AI for alternative strategy
                fallback_prompt = f"""
                The {strategy.__class__.__name__} strategy failed for {url}.
                Error: {str(e)}
                
                Suggest an alternative strategy from: {list(self.strategies.keys())}
                Consider the original analysis: {json.dumps(analysis.__dict__, default=str)}
                
                Respond with just the strategy name.
                """
                
                try:
                    fallback_response = await self._call_llm(fallback_prompt)
                    fallback_strategy_name = fallback_response.get('strategy', 'BrowserAutonomousStrategy')
                    
                    if fallback_strategy_name in self.strategies:
                        fallback_strategy = self.strategies[fallback_strategy_name]()
                        results = await fallback_strategy.extract(url, search_query, max_results)
                        
                        if results:
                            await self.learn_from_extraction(url, fallback_strategy_name, results, True)
                            self.data_handler.save_to_csv(results, output_file)
                            logger.info(f"Fallback successful: {len(results)} records saved")
                        
                        return results
                        
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
            
            raise