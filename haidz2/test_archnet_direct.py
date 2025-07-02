#!/usr/bin/env python3
"""
Direct test of ArchNet extraction bypassing the browser automation.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.modules.archnet_extractor import ArchNetExtractor
from src.modules.data_handler import DataHandler
from src.models.schemas import ArchiveRecord


def main():
    print("🏛️  Testing ArchNet Direct Extraction")
    print("=" * 50)
    
    extractor = ArchNetExtractor()
    data_handler = DataHandler()
    
    # Extract first page of sites
    print("\nExtracting sites from ArchNet page 1...")
    sites = extractor.extract_sites_list(1)
    
    print(f"✅ Extracted {len(sites)} sites")
    
    if sites:
        # Convert to ArchiveRecord format
        records = []
        for site in sites:
            try:
                record = ArchiveRecord(
                    title=site.get('title', ''),
                    location=site.get('location', ''),
                    collection='ArchNet',
                    inventory_num=site.get('inventory_num', ''),
                    typ=site.get('type', ''),
                    notes=site.get('description', ''),
                    image_url=site.get('image_url', '')
                )
                records.append(record)
            except Exception as e:
                print(f"Error creating record: {e}")
        
        # Save to CSV
        if records:
            output_file = "archnet_direct_extract.csv"
            data_handler.save_to_csv(records, output_file)
            print(f"\n✅ Saved {len(records)} records to {output_file}")
            
            # Show sample
            print("\nSample records:")
            for i, record in enumerate(records[:3]):
                print(f"\n{i+1}. {record.title}")
                print(f"   Location: {record.orig_location}")
                print(f"   Type: {record.typ}")
                print(f"   ID: {record.inventory_num}")
    else:
        print("\n❌ No sites extracted")
        
        # Try with curl to debug
        print("\nTrying direct curl request...")
        import subprocess
        result = subprocess.run([
            'curl', '-s', 
            'https://www.archnet.org/sites/category/all/1',
            '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            '-H', 'Accept: text/html,application/xhtml+xml'
        ], capture_output=True, text=True)
        
        # Check if we got the page
        if '__NEXT_DATA__' in result.stdout:
            print("✅ Page contains __NEXT_DATA__")
            
            # Save for debugging
            with open('archnet_debug.html', 'w') as f:
                f.write(result.stdout)
            print("💾 Saved page to archnet_debug.html for debugging")
        else:
            print("❌ Page doesn't contain expected data")


if __name__ == "__main__":
    main()