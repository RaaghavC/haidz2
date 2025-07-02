#!/usr/bin/env python3
"""
Enhanced main entry point for the Historical Architecture Scraper.
Designed to work with real-world archive websites.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.cli_enhanced import scrape


if __name__ == "__main__":
    scrape()