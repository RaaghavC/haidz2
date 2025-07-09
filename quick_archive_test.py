#!/usr/bin/env python3
"""
Quick test of one archive to show CSV output.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agent.robust_orchestrator import RobustOrchestrator


async def main():
    """Quick test."""
    
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set!")
        return
    
    print("QUICK ARCHIVE TEST - ArchNet")
    print("="*40)
    
    orchestrator = RobustOrchestrator(
        api_key=os.getenv("OPENAI_API_KEY"),
        provider="openai",
        headless=True
    )
    
    result = await orchestrator.scrape(
        start_url="https://www.archnet.org/",
        search_query="Antakya",
        max_results=3,
        max_pages=1
    )
    
    print(f"Success: {result.success}")
    print(f"Items: {result.items_scraped}")
    
    # Show most recent CSV file
    import glob
    csv_files = glob.glob("csv/robust_scrape_results_*.csv")
    if csv_files:
        latest_csv = max(csv_files)
        print(f"\nLatest CSV: {latest_csv}")


if __name__ == "__main__":
    asyncio.run(main())