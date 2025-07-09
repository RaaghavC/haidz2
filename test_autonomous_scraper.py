#!/usr/bin/env python3
"""
Test the autonomous navigation capabilities of the robust scraper.
This tests the scraper's ability to start from a landing page and 
find actual image records.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agent.robust_orchestrator import RobustOrchestrator


async def test_autonomous_scraping():
    """Test autonomous navigation on different archives."""
    
    # Test cases with expected autonomous behavior
    test_cases = [
        {
            "name": "ArchNet - Find Antakya Images",
            "url": "https://www.archnet.org/",
            "search": "Antakya",
            "description": "Should navigate from homepage to find Antakya images"
        },
        {
            "name": "Manar al-Athar - Find Antioch Photos",
            "url": "https://www.manar-al-athar.ox.ac.uk/",
            "search": "Antioch",
            "description": "Should use search and navigate to individual photos"
        },
        {
            "name": "SALT Research - Turkish Archives",
            "url": "https://saltresearch.org/",
            "search": "Antakya",
            "description": "Should explore site to find Antakya materials"
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing: {test['name']}")
        print(f"URL: {test['url']}")
        print(f"Search: {test['search']}")
        print(f"Expected: {test['description']}")
        print('='*60)
        
        try:
            # Create orchestrator
            orchestrator = RobustOrchestrator(
                api_key=os.getenv("OPENAI_API_KEY"),
                provider="openai",
                headless=True  # Run headless to avoid timeout
            )
            
            # Run scraping with autonomous navigation
            result = await orchestrator.scrape(
                start_url=test['url'],
                search_query=test['search'],
                max_results=5,  # Get up to 5 images
                max_pages=3     # Explore up to 3 pages
            )
            
            # Display results
            print(f"\nResults:")
            print(f"  Success: {result.success}")
            print(f"  Images found: {result.items_scraped}")
            
            if result.items:
                print(f"\n  Extracted items:")
                for i, item in enumerate(result.items[:3]):
                    print(f"\n  {i+1}. {item.title or 'Untitled'}")
                    print(f"     Type: {item.typ}")
                    print(f"     Location: {item.orig_location}")
                    print(f"     Collection: {item.collection}")
                    print(f"     Date: {item.ce_start_date} - {item.ce_end_date}")
                    if item.notes:
                        print(f"     Notes: {item.notes[:100]}...")
            else:
                print("  No items extracted")
            
            # Show navigation stats
            if result.metadata:
                stats = result.metadata.get('stats', {})
                print(f"\n  Navigation statistics:")
                print(f"     Pages explored: {stats.get('total_pages_visited', 0)}")
                print(f"     Items found: {stats.get('total_items_found', 0)}")
                print(f"     Items filtered: {stats.get('total_items_filtered', 0)}")
                
        except Exception as e:
            print(f"\nError: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Pause between tests
        print("\nPausing before next test...")
        await asyncio.sleep(5)


async def test_specific_archive():
    """Test a specific archive in detail."""
    
    print("\n" + "="*60)
    print("DETAILED TEST: ArchNet Antakya Search")
    print("="*60)
    
    orchestrator = RobustOrchestrator(
        api_key=os.getenv("OPENAI_API_KEY"),
        provider="openai",
        headless=True  # Run headless
    )
    
    # Enable detailed logging
    import logging
    logging.getLogger("src.agent.autonomous_navigator").setLevel(logging.DEBUG)
    
    result = await orchestrator.scrape(
        start_url="https://www.archnet.org/",
        search_query="Antakya mosque",
        max_results=10,
        max_pages=5
    )
    
    print(f"\nDetailed Results:")
    print(f"Total images extracted: {result.items_scraped}")
    
    if result.items:
        # Save to CSV for inspection
        import pandas as pd
        data = [item.dict() for item in result.items]
        df = pd.DataFrame(data)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"csv/autonomous_test_{timestamp}.csv"
        df.to_csv(filename, index=False)
        print(f"Saved results to: {filename}")
        
        # Show sample of data
        print("\nSample of extracted data:")
        print(df[['title', 'typ', 'orig_location', 'collection']].head(10))


async def main():
    """Run all tests."""
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set!")
        return
    
    print("AUTONOMOUS SCRAPER TEST")
    print("=======================")
    print("Testing the scraper's ability to autonomously navigate")
    print("from landing pages to find actual image records.")
    
    # Run basic tests
    await test_autonomous_scraping()
    
    # Run detailed test
    #await test_specific_archive()
    
    print("\n\nTEST COMPLETE!")


if __name__ == "__main__":
    # Set up logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    asyncio.run(main())