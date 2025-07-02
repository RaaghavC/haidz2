#!/usr/bin/env python3
"""Test Manar al-Athar direct HTTP extraction."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.modules.manar_extractor import ManarExtractor
from src.modules.data_handler import DataHandler
from src.models.schemas import ArchiveRecord


def main():
    print("🏛️  Testing Manar al-Athar Direct Extraction")
    print("=" * 50)
    
    extractor = ManarExtractor()
    data_handler = DataHandler()
    
    # Extract first page of photos
    print("\nExtracting photos from Manar al-Athar page 1...")
    photos = extractor.extract_search_results(1)
    
    print(f"✅ Extracted {len(photos)} photos")
    
    if photos:
        # Convert to ArchiveRecord format
        records = []
        for photo in photos:
            try:
                record = ArchiveRecord(
                    title=photo.get('title', ''),
                    orig_location=photo.get('location', ''),
                    collection='Manar al-Athar',
                    inventory_num=photo.get('inventory_num', ''),
                    typ=photo.get('type', ''),
                    notes=photo.get('notes', ''),
                    image_url=photo.get('image_url', '')
                )
                records.append(record)
            except Exception as e:
                print(f"Error creating record: {e}")
        
        # Save to CSV
        if records:
            output_file = "manar_direct_extract.csv"
            data_handler.save_to_csv(records, output_file)
            print(f"\n✅ Saved {len(records)} records to {output_file}")
            
            # Show sample
            print("\nSample records:")
            for i, record in enumerate(records[:3]):
                print(f"\n{i+1}. {record.title}")
                print(f"   Location: {record.orig_location}")
                print(f"   Type: {record.typ}")
                print(f"   ID: {record.inventory_num}")
                print(f"   Collection: {record.collection}")
        else:
            print("\n❌ No valid records created")
    else:
        print("\n❌ No photos extracted")
        
        # Get total results for debugging
        total = extractor.get_total_results()
        print(f"Total results available: {total}")


if __name__ == "__main__":
    main()