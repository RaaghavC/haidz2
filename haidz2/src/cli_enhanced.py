"""Enhanced command-line interface for real-world archive scraping."""

import asyncio
import click
from pathlib import Path
from typing import Optional
import sys

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
    default=5,
    type=int,
    help='Maximum number of pages to scrape (default: 5)'
)
@click.option(
    '--headless/--no-headless',
    default=True,
    help='Run browser in headless mode'
)
@click.option(
    '--max-retries', '-r',
    default=2,
    type=int,
    help='Maximum retry attempts for self-correction'
)
@click.option(
    '--min-quality', '-q',
    default=0.3,
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
@click.option(
    '--screenshot/--no-screenshot',
    default=True,
    help='Take screenshots during scraping'
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
    no_self_correction: bool,
    screenshot: bool
) -> None:
    """
    Enhanced Historical Architecture Scraper
    
    Autonomously extracts metadata from digital archives using intelligent
    analysis and self-correction.
    
    Supported archives:
    - ArchNet (archnet.org)
    - Manar al-Athar (manar-al-athar.ox.ac.uk)
    - SALT Research (saltresearch.org)
    - Machiel Kiel Archive (nit-istanbul.org)
    - And many more...
    
    Examples:
    
        # Scrape ArchNet collections
        python main_enhanced.py https://www.archnet.org/collections
        
        # Scrape with custom settings
        python main_enhanced.py https://archnet.org -o archnet_data.csv -p 10
        
        # Scrape with visible browser
        python main_enhanced.py https://archnet.org --no-headless
    """
    
    print(f"\n🏛️  Historical Architecture Scraper (Enhanced)")
    print(f"{'='*50}")
    print(f"📍 Target URL: {url}")
    print(f"📄 Output file: {output}")
    print(f"📑 Max pages: {max_pages}")
    print(f"🤖 Headless: {headless}")
    print(f"{'='*50}\n")
    
    # Validate URL
    if not url.startswith(('http://', 'https://')):
        click.echo("❌ Error: URL must start with http:// or https://", err=True)
        sys.exit(1)
    
    # Create output directory if needed
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create configuration
    config = AgentConfig(
        output_file=str(output_path),
        max_pages=max_pages,
        headless=headless,
        max_correction_attempts=max_retries,
        min_quality_threshold=min_quality,
        save_intermediate=save_intermediate,
        log_level="DEBUG" if verbose else "INFO",
        enable_self_correction=not no_self_correction,
        screenshot_on_error=screenshot
    )
    
    # Create and run agent
    agent = EnhancedAutonomousScrapingAgent(
        target_url=url,
        config=config
    )
    
    try:
        # Run the async agent
        asyncio.run(agent.run())
        
        click.echo(f"\n✅ Scraping completed successfully!")
        click.echo(f"📊 Data saved to: {output}")
        
        # Show summary statistics
        try:
            import pandas as pd
            df = pd.read_csv(output)
            click.echo(f"\n📈 Summary:")
            click.echo(f"   - Total records: {len(df)}")
            click.echo(f"   - Fields populated: {df.notna().sum().sum()} / {df.size}")
            click.echo(f"   - Completeness: {(df.notna().sum().sum() / df.size) * 100:.1f}%")
        except:
            pass
        
    except KeyboardInterrupt:
        click.echo("\n\n⚠️  Scraping interrupted by user")
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    scrape()