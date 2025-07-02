"""
Browser-based autonomous extraction strategy for unknown archives
Uses the existing autonomous scraper with search filtering
"""

import logging
from typing import List, Dict, Any
import asyncio

from src.strategies.base_strategy import BaseExtractionStrategy
from src.agent.enhanced_orchestrator import EnhancedAutonomousScrapingAgent
from src.agent.config import AgentConfig
from src.models.schemas import ArchiveRecord

logger = logging.getLogger(__name__)


class BrowserAutonomousStrategy(BaseExtractionStrategy):
    """
    Fallback strategy using autonomous browser-based extraction
    Works with any archive by analyzing DOM patterns
    """
    
    def __init__(self):
        super().__init__()
        
    async def extract(
        self, 
        url: str, 
        search_query: str = "",
        max_results: int = 500
    ) -> List[ArchiveRecord]:
        """
        Extract data using autonomous browser-based scraping
        """
        logger.info(f"🤖 Browser Autonomous Strategy: Extracting from {url}")
        if search_query:
            logger.info(f"🔍 Search query: '{search_query}'")
        
        # Configure the autonomous agent
        config = AgentConfig(
            output_file='temp_autonomous_output.csv',
            max_pages=10,  # Limit pages for efficiency
            headless=True,
            max_correction_attempts=2,
            min_quality_threshold=0.3,  # Lower threshold for unknown sites
            save_intermediate=False,
            log_level="INFO",
            enable_self_correction=True
        )
        
        # Create and run the autonomous agent
        agent = EnhancedAutonomousScrapingAgent(
            target_url=url,
            config=config
        )
        
        try:
            # Run the agent
            await agent.run()
            
            # Load the extracted data
            import csv
            all_records = []
            
            try:
                with open('temp_autonomous_output.csv', 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Convert CSV row to our format
                        record = {
                            'unique_id': row.get('Unique ID', ''),
                            'type': row.get('Typ', 'Image'),
                            'title': row.get('Title', ''),
                            'ce_start_date': row.get('CE Start Date'),
                            'ce_end_date': row.get('CE End Date'),
                            'ah_start_date': row.get('AH Start Date'),
                            'ah_end_date': row.get('AH End Date'),
                            'date_photo_taken': row.get('Date photograph taken'),
                            'date_qualif': row.get('Date Qualif.'),
                            'medium': row.get('Medium'),
                            'technique': row.get('Technique'),
                            'measurements': row.get('Measurements'),
                            'artist': row.get('Artist'),
                            'orig_location': row.get('Orig. Location'),
                            'collection': row.get('Collection'),
                            'inventory_num': row.get('Inventory #'),
                            'folder': row.get('Folder'),
                            'photographer': row.get('Photographer'),
                            'copyright_photo': row.get('Copyright for Photo'),
                            'image_quality': row.get('Image Quality'),
                            'image_rights': row.get('Image Rights'),
                            'published_in': row.get('Published in'),
                            'notes': row.get('Notes')
                        }
                        all_records.append(record)
                        
                        if len(all_records) >= max_results:
                            break
                            
            except FileNotFoundError:
                logger.warning("No data extracted by autonomous agent")
                return []
            
            # Filter by search query
            if search_query and all_records:
                all_records = self.filter_by_search_query(all_records, search_query)
            
            logger.info(f"✅ Extracted {len(all_records)} records using autonomous browser")
            
            # Clean up temp file
            import os
            if os.path.exists('temp_autonomous_output.csv'):
                os.remove('temp_autonomous_output.csv')
            
            # Convert to ArchiveRecord objects
            return self.convert_to_archive_records(all_records)
            
        except Exception as e:
            logger.error(f"Autonomous extraction failed: {e}")
            return []