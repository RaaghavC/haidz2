#!/usr/bin/env python3
"""
Test each archive individually to get clear results.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agent.robust_orchestrator import RobustOrchestrator


async def test_single_archive(name: str, url: str, search_term: str):
    """Test a single archive and return immediately."""
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"Search: {search_term}")
    print(f"Time: {datetime.now()}")
    print('='*70)
    
    orchestrator = RobustOrchestrator(
        api_key=os.getenv("OPENAI_API_KEY"),
        provider="openai",
        headless=True
    )
    
    try:
        # Very minimal test - just 2 results, 1 page
        result = await orchestrator.scrape(
            start_url=url,
            search_query=search_term,
            max_results=2,
            max_pages=1
        )
        
        print(f"\nSTATUS: {'✓ SUCCESS' if result.success else '✗ FAILED'}")
        print(f"Items extracted: {result.items_scraped}")
        
        if result.items:
            print("\nExtracted items:")
            for i, item in enumerate(result.items):
                print(f"  {i+1}. {item.title or 'Untitled'}")
                print(f"     Location: {item.orig_location}")
                print(f"     Type: {item.typ}")
        
        # Show stats
        if result.metadata:
            stats = result.metadata.get('stats', {})
            print(f"\nStats:")
            print(f"  Pages visited: {stats.get('total_pages_visited', 0)}")
            print(f"  Duration: {result.metadata.get('duration_seconds', 0):.1f}s")
        
        return result.success, result.items_scraped
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        return False, 0


async def main():
    """Test each archive individually."""
    
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set!")
        return
    
    print("INDIVIDUAL ARCHIVE TESTS")
    print("="*70)
    print("Testing each archive with autonomous navigation")
    print("NO hardcoding, NO special treatment\n")
    
    # Test 1: ArchNet
    print("\n[1/5] ARCHNET TEST")
    success1, items1 = await test_single_archive(
        "ArchNet",
        "https://www.archnet.org/",
        "Antakya"
    )
    
    # Test 2: NYU Akkasah
    print("\n\n[2/5] NYU AKKASAH CENTER TEST")
    success2, items2 = await test_single_archive(
        "NYU Abu Dhabi - Akkasah Center",
        "https://nyuad.nyu.edu/en/research/faculty-labs-and-projects/akkasah-center-for-photography.html",
        "Antakya"
    )
    
    # Test 3: Manar al-Athar
    print("\n\n[3/5] MANAR AL-ATHAR TEST")
    success3, items3 = await test_single_archive(
        "Manar al-Athar",
        "https://www.manar-al-athar.ox.ac.uk/pages/collections_featured.php?login=true",
        "Antioch"
    )
    
    # Test 4: SALT Research
    print("\n\n[4/5] SALT RESEARCH TEST")
    success4, items4 = await test_single_archive(
        "SALT Research",
        "https://saltresearch.org/discovery/search?vid=90GARANTI_INST:90SALT_VU1&lang=en",
        "Antakya"
    )
    
    # Test 5: NIT Istanbul
    print("\n\n[5/5] NIT ISTANBUL TEST")
    success5, items5 = await test_single_archive(
        "NIT Istanbul - Machiel Kiel Archive",
        "https://www.nit-istanbul.org/projects/machiel-kiel-photographic-archive",
        "Antakya"
    )
    
    # Final Summary
    print("\n\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    
    results = [
        ("ArchNet", success1, items1),
        ("NYU Akkasah", success2, items2),
        ("Manar al-Athar", success3, items3),
        ("SALT Research", success4, items4),
        ("NIT Istanbul", success5, items5)
    ]
    
    successful = sum(1 for _, s, _ in results if s)
    total_items = sum(i for _, _, i in results)
    
    print(f"\nSuccess rate: {successful}/5 archives ({successful*20}%)")
    print(f"Total items extracted: {total_items}")
    
    print("\nDetailed results:")
    for name, success, items in results:
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"  {name}: {status} - {items} items")
    
    print("\nTEST COMPLETE!")


if __name__ == "__main__":
    # Set timeout for the entire script
    import signal
    
    def timeout_handler(signum, frame):
        print("\n\nTIMEOUT: Test taking too long, exiting...")
        sys.exit(1)
    
    # Set 8 minute timeout for entire test
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(480)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    finally:
        signal.alarm(0)  # Cancel the alarm