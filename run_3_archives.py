#!/usr/bin/env python3
"""
Run autonomous scraper on 3 different archives and show CSV output.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agent.robust_orchestrator import RobustOrchestrator


async def test_archive(name: str, url: str, search_term: str):
    """Test a single archive and save results."""
    print(f"\n{'='*60}")
    print(f"TESTING: {name}")
    print(f"URL: {url}")
    print(f"Search: {search_term}")
    print('='*60)
    
    orchestrator = RobustOrchestrator(
        api_key=os.getenv("OPENAI_API_KEY"),
        provider="openai",
        headless=True
    )
    
    try:
        result = await orchestrator.scrape(
            start_url=url,
            search_query=search_term,
            max_results=200,  # Get 200 items from each
            max_pages=10     # Explore 10 pages max
        )
        
        print(f"\nRESULT: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Items extracted: {result.items_scraped}")
        
        if result.items:
            print("\nExtracted items:")
            for i, item in enumerate(result.items):
                print(f"  {i+1}. {item.title or 'Untitled'}")
                print(f"     Location: {item.orig_location}")
                print(f"     Collection: {item.collection}")
        
        return result.success, result.items_scraped, name
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        return False, 0, name


async def main():
    """Run 3 archive tests."""
    
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set!")
        return
    
    print("AUTONOMOUS SCRAPER - 3 ARCHIVE TEST")
    print("="*60)
    print(f"Start time: {datetime.now()}")
    
    # Test 3 different archives
    archives = [
        ("ArchNet", "https://www.archnet.org/", "Antakya"),
        ("Manar al-Athar", "https://www.manar-al-athar.ox.ac.uk/", "Antioch"),
        ("SALT Research", "https://saltresearch.org/", "Antakya")
    ]
    
    results = []
    for name, url, search in archives:
        success, items, archive_name = await test_archive(name, url, search)
        results.append((archive_name, success, items))
        
        # Brief pause between tests
        await asyncio.sleep(3)
    
    # Summary
    print("\n\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    for name, success, items in results:
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{name}: {status} - {items} items")
    
    # Show CSV files created
    print(f"\nCSV files created in csv/ directory:")
    print("Check the most recent robust_scrape_results_*.csv files")
    
    print(f"\nTest completed: {datetime.now()}")


if __name__ == "__main__":
    asyncio.run(m