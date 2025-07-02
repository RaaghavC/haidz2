"""
Base Strategy Interface for Archive Extraction
All extraction strategies must implement this interface
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

from src.models.schemas import ArchiveRecord

logger = logging.getLogger(__name__)


class BaseExtractionStrategy(ABC):
    """
    Abstract base class for all extraction strategies
    Implements the Strategy pattern for different archive types
    """
    
    def __init__(self):
        self.name = self.__class__.__name__
        
    @abstractmethod
    async def extract(
        self, 
        url: str, 
        search_query: str = "",
        max_results: int = 500
    ) -> List[ArchiveRecord]:
        """
        Extract data from the archive
        
        Args:
            url: The archive URL to scrape
            search_query: Optional search query to filter results
            max_results: Maximum number of results to return
            
        Returns:
            List of ArchiveRecord objects
        """
        pass
    
    def filter_by_search_query(
        self, 
        records: List[Dict[str, Any]], 
        search_query: str
    ) -> List[Dict[str, Any]]:
        """
        Filter records based on search query
        Searches across all text fields
        """
        if not search_query:
            return records
            
        search_terms = search_query.lower().split()
        filtered = []
        
        for record in records:
            # Convert all values to lowercase strings for searching
            record_text = ' '.join(
                str(v).lower() for v in record.values() if v
            )
            
            # Check if all search terms appear in the record
            if all(term in record_text for term in search_terms):
                filtered.append(record)
                
        logger.info(f"Filtered {len(records)} records to {len(filtered)} matching '{search_query}'")
        return filtered
    
    def convert_to_archive_records(
        self, 
        raw_records: List[Dict[str, Any]]
    ) -> List[ArchiveRecord]:
        """
        Convert raw dictionaries to ArchiveRecord objects
        """
        archive_records = []
        
        for raw in raw_records:
            try:
                # Map raw fields to ArchiveRecord schema
                record = ArchiveRecord(
                    unique_id=raw.get('unique_id', ''),
                    typ=raw.get('type', raw.get('typ', 'Image')),
                    title=raw.get('title', raw.get('name', '')),
                    ce_start_date=raw.get('ce_start_date'),
                    ce_end_date=raw.get('ce_end_date'),
                    ah_start_date=raw.get('ah_start_date'),
                    ah_end_date=raw.get('ah_end_date'),
                    date_photo_taken=raw.get('date_photo_taken', raw.get('year')),
                    date_qualif=raw.get('date_qualif'),
                    medium=raw.get('medium', raw.get('media_type')),
                    technique=raw.get('technique'),
                    measurements=raw.get('measurements'),
                    artist=raw.get('artist', raw.get('photographer')),
                    orig_location=raw.get('orig_location', raw.get('place_name')),
                    collection=raw.get('collection', raw.get('source')),
                    inventory_num=raw.get('inventory_num', raw.get('record_id')),
                    folder=raw.get('folder'),
                    photographer=raw.get('photographer'),
                    copyright_photo=raw.get('copyright_photo', raw.get('copyright')),
                    image_quality=raw.get('image_quality', raw.get('content_url')),
                    image_rights=raw.get('image_rights', raw.get('iiif_url')),
                    published_in=raw.get('published_in'),
                    notes=raw.get('notes', raw.get('caption', raw.get('description')))
                )
                archive_records.append(record)
            except Exception as e:
                logger.warning(f"Failed to convert record: {e}")
                continue
                
        return archive_records