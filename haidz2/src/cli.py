"""Command-line interface for the autonomous scraping agent."""

import asyncio
import click
from pathlib import Path
from typing import Optional

from src.agent.enhanced_orchestrator import EnhancedAutonomousScrapingAgent
from src.agent.config import AgentConfig


@click.command()
@click.argument('url', type=str)
@click.option(
    '--output', '-o',
    default='scraped_data.csv',
    help='Output CSV file path'
)
@click.option(
    '--max-pages', '-p',
    default=100,
    type=int,
    help='Maximum number of pages to scrape'
)
@click.option(
    '--headless/--no-headless',
    default=True,
    help='Run browser in headless mode'
)
@click.option(
    '--max-retries', '-r',
    default=3,
    type=int,
    help='Maximum retry attempts for self-correction'
)
@click.option(
    '--min-quality', '-q',
    default=0.6,
    type=float,
    help='Minimum quality threshold (0.0-1.0)'
)
@click.option(
    '--save-intermediate/--no-save-intermediate',
    default=True,
    help='Save data after each page'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
@click.option(
    '--no-self-correction',
    is_flag=True,
    help='Disable self-correction mechanism'
)
def scrape(
    url: str,
    output: str,
    max_pages: int,
    headless: bool,
    max_retries: int,
    min_quality: float,
    save_intermediate: bool,
    verbose: bool,
    no_self_correction: bool
) -> None:
    """
    Autonomous web scraper for digital archives.
    
    This tool intelligently analyzes and extracts metadata from digital archives
    using a cognitive loop approach: Analyze → Plan → Execute → Verify.
    
    Example:
        python -m src.cli https://example-archive.org --output data.csv
    """
    click.echo(f"🤖 Historical Architecture Scraper")
    click.echo(f"📍 Target URL: {url}")
    click.echo(f"📄 Output file: {output}")
    
    # Create configuration
    config = AgentConfig(
        output_file=output,
        max_pages=max_pages,
        headless=headless,
        max_correction_attempts=max_retries,
        min_quality_threshold=min_quality,
        save_intermediate=save_intermediate,
        log_level="DEBUG" if verbose else "INFO",
        enable_self_correction=not no_self_correction
    )
    
    # Create and run agent
    agent = EnhancedAutonomousScrapingAgent(
        target_url=url,
        config=config
    )
    
    try:
        # Run the async agent
        asyncio.run(agent.run())
        
        click.echo(f"✅ Scraping completed successfully!")
        click.echo(f"📊 Data saved to: {output}")
        
    except KeyboardInterrupt:
        click.echo("\n⚠️  Scraping interrupted by user")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.ClickException(str(e))


if __name__ == '__main__':
    scrape()