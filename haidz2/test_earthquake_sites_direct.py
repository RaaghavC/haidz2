#!/usr/bin/env python3
"""
Direct test of earthquake sites using ArchNet's Algolia API
"""

import asyncio
import logging
from src.strategies.archnet_strategy import ArchNetStrategy
from src.modules.data_handler import DataHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Earthquake-affected sites to search
SITES = [
    "Habib-i Neccar Mosque",
    "Gaziantep Castle",
    "Aleppo Citadel",
    "Antakya",
    "earthquake"
]

async def test_earthquake_sites():
    """Test searching for earthquake-affected sites"""
    
    strategy = ArchNetStrategy()
    data_handler = DataHandler()
    
    for site in SITES:
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 Searching for: {site}")
        logger.info("="*60)
        
        try:
            results = await strategy.extract(
                url="https://www.archnet.org",
                search_query=site,
                max_results=5
            )
            
            logger.info(f"✅ Found {len(results)} results")
            
            if results:
                # Save to CSV
                filename = f"earthquake_{site.replace(' ', '_').lower()}.csv"
                data_handler.save_to_csv(results, filename)
                logger.info(f"💾 Saved to: {filename}")
                
                # Show sample
                logger.info("\n📋 Sample results:")
                for i, record in enumerate(results[:3]):
                    logger.info(f"\n  {i+1}. {record.title}")
                    logger.info(f"     Location: {record.orig_location}")
                    logger.info(f"     Collection: {record.collection}")
                    if record.notes:
                        logger.info(f"     Notes: {record.notes[:100]}...")
            else:
                logger.info("❌ No results found")
                
        except Exception as e:
            logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_earthquake_sites())