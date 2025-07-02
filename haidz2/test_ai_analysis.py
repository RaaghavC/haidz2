#!/usr/bin/env python3
"""
Quick test of AI Brain's analysis capabilities
"""

import asyncio
import logging
from dotenv import load_dotenv
from src.agent.true_ai_brain import TrueAIBrain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

async def test_analysis():
    """Test AI brain analysis for different archives"""
    
    brain = TrueAIBrain()
    
    archives = [
        "https://www.archnet.org",
        "https://commons.wikimedia.org",
        "https://www.manar-al-athar.ox.ac.uk"
    ]
    
    for url in archives:
        logger.info(f"\n{'='*60}")
        logger.info(f"Analyzing: {url}")
        logger.info("="*60)
        
        analysis = await brain.analyze_archive_with_ai(url)
        
        logger.info(f"\nResults:")
        logger.info(f"Type: {analysis.archive_type}")
        logger.info(f"Strategy: {analysis.recommended_strategy}")
        logger.info(f"Confidence: {analysis.confidence:.1%}")
        logger.info(f"Has API: {analysis.characteristics.get('has_api', False)}")
        logger.info(f"API Type: {analysis.characteristics.get('api_type', 'none')}")
        
        if analysis.extraction_hints.get('api_endpoints'):
            logger.info(f"API Endpoints: {analysis.extraction_hints['api_endpoints']}")

if __name__ == "__main__":
    asyncio.run(test_analysis())