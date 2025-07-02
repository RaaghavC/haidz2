"""
AI Brain for Autonomous Scraping Decision-Making
Intelligently analyzes archives and selects optimal extraction strategies
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, Type
from urllib.parse import urlparse
from abc import ABC, abstractmethod
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


class AIScrapingBrain:
    """
    Intelligent AI agent that autonomously decides extraction strategies
    based on archive analysis and selects the optimal approach
    """
    
    def __init__(self):
        self.strategies: Dict[str, Type[BaseExtractionStrategy]] = {
            'archnet.org': ArchNetStrategy,
            'commons.wikimedia.org': WikimediaStrategy,
            'manar-al-athar.ox.ac.uk': ManarStrategy,
            'saltresearch.org': BrowserAutonomousStrategy,  # Known slow site
            'nit-istanbul.org': BrowserAutonomousStrategy,  # Known slow site
        }
        self.data_handler = DataHandler()
        
    async def analyze_archive(self, url: str) -> Dict[str, Any]:
        """
        Intelligently analyze the archive to determine its characteristics
        """
        logger.info(f"🧠 AI Brain analyzing: {url}")
        
        analysis = {
            'url': url,
            'domain': urlparse(url).netloc,
            'has_api': False,
            'api_type': None,
            'javascript_heavy': False,
            'requires_auth': False,
            'archive_type': 'unknown',
            'confidence': 0.0,
            'recommended_strategy': None
        }
        
        # Check for known archives first
        domain = analysis['domain']
        
        # Also check subdomains
        for known_domain in self.strategies.keys():
            if known_domain in domain:
                analysis['archive_type'] = 'known'
                analysis['confidence'] = 0.95
                analysis['recommended_strategy'] = self.strategies[known_domain]
                logger.info(f"✅ Recognized known archive: {known_domain}")
                return analysis
        
        # For unknown archives, perform intelligent detection
        try:
            # First, try API detection
            api_detector = APIDetectionStrategy()
            api_info = await api_detector.detect_api(url)
            
            if api_info['has_api']:
                analysis['has_api'] = True
                analysis['api_type'] = api_info['api_type']
                analysis['confidence'] = 0.8
                analysis['recommended_strategy'] = APIDetectionStrategy
                logger.info(f"🔍 Detected API: {api_info['api_type']}")
                return analysis
            
            # Check if JavaScript-heavy site
            async with aiohttp.ClientSession() as session:
                try:
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    
                    async with session.get(url, ssl=ssl_context, timeout=10) as response:
                        content = await response.text()
                        
                        # Heuristics for JavaScript detection
                        js_indicators = [
                            'react', 'vue', 'angular', 'webpack',
                            '__NEXT_DATA__', 'window.__INITIAL_STATE__',
                            'require.config', 'data-react', 'ng-app'
                        ]
                        
                        js_count = sum(1 for indicator in js_indicators if indicator in content.lower())
                        if js_count >= 2:
                            analysis['javascript_heavy'] = True
                            
                except Exception as e:
                    logger.warning(f"Error analyzing site content: {e}")
            
            # Decide strategy based on analysis
            if analysis['javascript_heavy']:
                analysis['recommended_strategy'] = BrowserAutonomousStrategy
                analysis['confidence'] = 0.7
                logger.info("🌐 Detected JavaScript-heavy site, using browser strategy")
            else:
                # Default to browser strategy for unknown sites
                analysis['recommended_strategy'] = BrowserAutonomousStrategy
                analysis['confidence'] = 0.6
                logger.info("📋 Using autonomous browser strategy for unknown archive")
                
        except Exception as e:
            logger.error(f"Error during archive analysis: {e}")
            # Fallback to browser strategy
            analysis['recommended_strategy'] = BrowserAutonomousStrategy
            analysis['confidence'] = 0.5
            
        return analysis
    
    async def scrape_intelligently(
        self, 
        url: str, 
        search_query: str = "",
        output_file: str = "scraped_data.csv",
        max_results: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Main entry point for intelligent scraping
        """
        logger.info("="*60)
        logger.info("🤖 AI-AGENTIC SCRAPING ENGINE ACTIVATED")
        logger.info("="*60)
        
        # Step 1: Analyze the archive
        logger.info("\n📊 PHASE 1: Archive Analysis")
        analysis = await self.analyze_archive(url)
        
        logger.info(f"Analysis Results:")
        logger.info(f"  - Archive Type: {analysis['archive_type']}")
        logger.info(f"  - Has API: {analysis['has_api']}")
        logger.info(f"  - JavaScript Heavy: {analysis['javascript_heavy']}")
        logger.info(f"  - Confidence: {analysis['confidence']:.1%}")
        logger.info(f"  - Strategy: {analysis['recommended_strategy'].__name__}")
        
        # Step 2: Initialize the selected strategy
        logger.info(f"\n⚙️  PHASE 2: Strategy Initialization")
        strategy_class = analysis['recommended_strategy']
        strategy = strategy_class()
        
        # Step 3: Execute extraction with search filtering
        logger.info(f"\n🔍 PHASE 3: Data Extraction")
        if search_query:
            logger.info(f"Search Filter: '{search_query}'")
        
        try:
            results = await strategy.extract(
                url=url,
                search_query=search_query,
                max_results=max_results
            )
            
            logger.info(f"\n✅ Extraction completed: {len(results)} records found")
            
            # Step 4: Save to CSV
            if results:
                logger.info(f"\n💾 PHASE 4: Saving Results")
                self.data_handler.save_to_csv(results, output_file)
                logger.info(f"Data saved to: {output_file}")
            else:
                logger.warning("No results found matching the criteria")
                
            return results
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            
            # Try fallback strategy if primary fails
            if analysis['confidence'] < 0.9:
                logger.info("\n🔄 Attempting fallback strategy...")
                fallback_strategy = BrowserAutonomousStrategy()
                try:
                    results = await fallback_strategy.extract(
                        url=url,
                        search_query=search_query,
                        max_results=max_results
                    )
                    
                    if results:
                        self.data_handler.save_to_csv(results, output_file)
                        logger.info(f"Fallback successful: {len(results)} records saved")
                    
                    return results
                except Exception as fallback_error:
                    logger.error(f"Fallback strategy also failed: {fallback_error}")
                    
            raise