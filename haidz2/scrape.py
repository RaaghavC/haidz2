#!/usr/bin/env python3
"""
Unified AI-Agentic Web Scraper for Historical Architecture
Single entry point with intelligent strategy selection
Usage: python3 scrape.py [URL] [SEARCH_QUERY]
"""

import sys
import asyncio
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import click

# Import the AI brain and strategies
try:
    from src.agent.true_ai_brain import TrueAIBrain
    AI_BRAIN_AVAILABLE = True
except ImportError:
    AI_BRAIN_AVAILABLE = False
    
from src.agent.ai_brain import AIScrapingBrain
from src.modules.data_handler import DataHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.command()
@click.argument('url', type=str)
@click.argument('search_query', type=str, required=False, default="")
@click.option(
    '--output', '-o',
    default='scraped_data.csv',
    help='Output CSV file path'
)
@click.option(
    '--max-results', '-m',
    default=500,
    type=int,
    help='Maximum number of results to scrape'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
@click.option(
    '--use-true-ai/--no-true-ai',
    default=True,
    help='Use true AI brain (requires OpenAI API key) or fallback to rule-based'
)
def scrape(url: str, search_query: str, output: str, max_results: int, verbose: bool, use_true_ai: bool):
    """
    AI-Agentic scraper that intelligently extracts architecture data from any digital archive.
    
    Examples:
        python3 scrape.py https://www.archnet.org "habib-i neccar mosque"
        python3 scrape.py https://commons.wikimedia.org "antakya"
        python3 scrape.py https://www.manar-al-athar.ox.ac.uk "damascus"
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    click.echo(f"🤖 AI-Agentic Historical Architecture Scraper")
    click.echo(f"🌐 Target: {url}")
    if search_query:
        click.echo(f"🔍 Search Query: {search_query}")
    click.echo(f"📊 Max Results: {max_results}")
    click.echo(f"📄 Output: {output}")
    click.echo("")
    
    try:
        # Check if true AI brain should be used
        use_ai = use_true_ai and AI_BRAIN_AVAILABLE
        
        if use_ai:
            import os
            if not os.getenv('OPENAI_API_KEY'):
                click.echo("⚠️  OPENAI_API_KEY not set. Falling back to rule-based system.")
                click.echo("   Set your API key: export OPENAI_API_KEY='your-key-here'")
                use_ai = False
        
        # Initialize appropriate brain
        if use_ai:
            try:
                brain = TrueAIBrain()
                click.echo("🧠 Using TRUE AI Brain (LLM-powered)")
            except Exception as e:
                click.echo(f"⚠️  Failed to initialize AI Brain: {e}")
                click.echo("   Falling back to rule-based system.")
                brain = AIScrapingBrain()
        else:
            brain = AIScrapingBrain()
            if use_true_ai:
                click.echo("📋 Using rule-based system (AI brain not available)")
            else:
                click.echo("📋 Using rule-based system (by user choice)")
        
        # Run the intelligent scraping process
        asyncio.run(brain.scrape_intelligently(
            url=url,
            search_query=search_query,
            output_file=output,
            max_results=max_results
        ))
        
        click.echo(f"\n✅ Scraping completed successfully!")
        click.echo(f"📊 Data saved to: {output}")
        
    except KeyboardInterrupt:
        click.echo("\n⚠️  Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        logger.exception("Scraping failed")
        sys.exit(1)


if __name__ == '__main__':
    scrape()