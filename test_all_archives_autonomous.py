#!/usr/bin/env python3
"""
Universal test for autonomous scraping across ALL archives.
NO hardcoding. NO special treatment for any archive.
The scraper must work autonomously for any archive site.
"""

import asyncio
import os
import sys
import logging
from datetime import datetime
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agent.robust_orchestrator import RobustOrchestrator


async def test_archive(url: str, name: str, search_term: str = "Antakya"):
    """
    Test a single archive with NO special treatment.
    
    Args:
        url: Archive URL
        name: Archive name for reporting
        search_term: What to search for
    """
    print(f"\n{'='*80}")
    print(f"TESTING: {name}")
    print(f"URL: {url}")
    print(f"Search term: {search_term}")
    print(f"Start time: {datetime.now()}")
    print('='*80)
    
    # Create orchestrator - same settings for ALL archives
    orchestrator = RobustOrchestrator(
        api_key=os.getenv("OPENAI_API_KEY"),
        provider="openai",
        headless=True  # Run headless for all
    )
    
    result = None
    try:
        # Run scraping - same parameters for ALL archives
        result = await orchestrator.scrape(
            start_url=url,
            search_query=search_term,
            max_results=10,  # Try to get 10 items from each
            max_pages=3      # Explore up to 3 pages
        )
        
        # Display results
        print(f"\nRESULTS:")
        print(f"  ✓ Success: {result.success}")
        print(f"  ✓ Images found: {result.items_scraped}")
        
        if result.items:
            print(f"\n  EXTRACTED ITEMS:")
            for i, item in enumerate(result.items[:5]):  # Show first 5
                print(f"\n  {i+1}. Title: {item.title or 'Untitled'}")
                print(f"     Type: {item.typ}")
                print(f"     Location: {item.orig_location}")
                print(f"     Collection: {item.collection}")
                print(f"     URL: {item.image_quality}")
        else:
            print("\n  ✗ NO ITEMS EXTRACTED")
        
        # Show statistics
        if result.metadata:
            stats = result.metadata.get('stats', {})
            print(f"\n  STATISTICS:")
            print(f"     Pages visited: {stats.get('total_pages_visited', 0)}")
            print(f"     Items found: {stats.get('total_items_found', 0)}")
            print(f"     Items extracted: {stats.get('total_items_extracted', 0)}")
            print(f"     Items verified: {stats.get('total_items_verified', 0)}")
            print(f"     Items filtered: {stats.get('total_items_filtered', 0)}")
            print(f"     Duration: {result.metadata.get('duration_seconds', 0):.2f} seconds")
        
        # Return test result
        return {
            'archive': name,
            'url': url,
            'success': result.success,
            'items_extracted': result.items_scraped,
            'duration': result.metadata.get('duration_seconds', 0) if result.metadata else 0,
            'pages_visited': stats.get('total_pages_visited', 0) if result.metadata else 0,
            'error': None
        }
        
    except Exception as e:
        print(f"\n  ✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'archive': name,
            'url': url,
            'success': False,
            'items_extracted': 0,
            'duration': 0,
            'pages_visited': 0,
            'error': str(e)
        }


async def run_all_tests():
    """Run tests on ALL archives with NO special treatment."""
    
    # Define ALL archives to test
    archives = [
        {
            'name': 'ArchNet',
            'url': 'https://www.archnet.org/',
            'search': 'Antakya'
        },
        {
            'name': 'NYU Abu Dhabi - Akkasah Center',
            'url': 'https://nyuad.nyu.edu/en/research/faculty-labs-and-projects/akkasah-center-for-photography.html',
            'search': 'Antakya'
        },
        {
            'name': 'Manar al-Athar',
            'url': 'https://www.manar-al-athar.ox.ac.uk/pages/collections_featured.php?login=true',
            'search': 'Antioch'  # They might use the ancient name
        },
        {
            'name': 'SALT Research',
            'url': 'https://saltresearch.org/discovery/search?vid=90GARANTI_INST:90SALT_VU1&lang=en',
            'search': 'Antakya'
        },
        {
            'name': 'NIT Istanbul - Machiel Kiel Archive',
            'url': 'https://www.nit-istanbul.org/projects/machiel-kiel-photographic-archive',
            'search': 'Antakya'
        }
    ]
    
    print("\n" + "="*80)
    print("AUTONOMOUS SCRAPER - UNIVERSAL TEST FOR ALL ARCHIVES")
    print("="*80)
    print(f"Test started: {datetime.now()}")
    print(f"Total archives to test: {len(archives)}")
    print("\nIMPORTANT: NO hardcoding, NO special treatment for any archive")
    print("The scraper must work autonomously for ANY archive site")
    
    # Run tests
    results = []
    for i, archive in enumerate(archives):
        print(f"\n\n[{i+1}/{len(archives)}] Testing {archive['name']}...")
        
        result = await test_archive(
            url=archive['url'],
            name=archive['name'],
            search_term=archive['search']
        )
        results.append(result)
        
        # Brief pause between archives
        if i < len(archives) - 1:
            print("\nPausing before next archive...")
            await asyncio.sleep(5)
    
    # Generate summary report
    print("\n\n" + "="*80)
    print("FINAL TEST REPORT")
    print("="*80)
    print(f"Test completed: {datetime.now()}")
    
    # Summary table
    df = pd.DataFrame(results)
    print("\nSUMMARY TABLE:")
    print(df.to_string(index=False))
    
    # Success rate
    successful = df[df['success'] == True]
    success_rate = (len(successful) / len(df)) * 100
    total_items = df['items_extracted'].sum()
    
    print(f"\nOVERALL RESULTS:")
    print(f"  Success rate: {success_rate:.1f}% ({len(successful)}/{len(df)} archives)")
    print(f"  Total items extracted: {total_items}")
    print(f"  Average items per successful archive: {total_items/len(successful) if len(successful) > 0 else 0:.1f}")
    
    # Detailed results for each archive
    print("\nDETAILED RESULTS:")
    for _, row in df.iterrows():
        status = "✓ SUCCESS" if row['success'] else "✗ FAILED"
        print(f"\n{row['archive']}:")
        print(f"  Status: {status}")
        print(f"  Items extracted: {row['items_extracted']}")
        print(f"  Pages visited: {row['pages_visited']}")
        print(f"  Duration: {row['duration']:.2f}s")
        if row['error']:
            print(f"  Error: {row['error']}")
    
    # Save detailed report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"csv/autonomous_test_report_{timestamp}.csv"
    df.to_csv(report_file, index=False)
    print(f"\nDetailed report saved to: {report_file}")
    
    return results


async def main():
    """Run the universal test."""
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set!")
        return
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run all tests
    await run_all_tests()
    
    print("\n\nUNIVERSAL TEST COMPLETE!")


if __name__ == "__main__":
    asyncio.run(main())