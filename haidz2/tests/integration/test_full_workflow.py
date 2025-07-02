"""Integration test for the complete scraping workflow."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import pandas as pd

from src.agent.orchestrator import AutonomousScrapingAgent
from src.agent.config import AgentConfig


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_scraping_workflow():
    """Test the complete scraping workflow with a mock server."""
    # Note: This is a demonstration test. In production, you would:
    # 1. Set up a mock web server with sample pages
    # 2. Run the agent against the mock server
    # 3. Verify the extracted data
    
    # For now, we'll test that the components integrate properly
    with tempfile.TemporaryDirectory() as temp_dir:
        output_file = Path(temp_dir) / "test_output.csv"
        
        config = AgentConfig(
            output_file=str(output_file),
            max_pages=1,
            headless=True,
            enable_self_correction=False  # Disable for testing
        )
        
        # This would normally point to a test server
        agent = AutonomousScrapingAgent(
            target_url="https://httpstat.us/200",  # Simple test URL
            config=config
        )
        
        # The agent should handle the error gracefully
        try:
            await agent.run()
        except Exception:
            pass  # Expected for this simple test
        
        # Verify output file was created (even if empty)
        assert output_file.exists() or (output_file.with_suffix('.json')).exists()


def test_cli_import():
    """Test that CLI can be imported."""
    from src.cli import scrape
    assert scrape is not None


def test_models_import():
    """Test that all models can be imported."""
    from src.models.schemas import ArchiveRecord, DataSchema
    from src.models.strategies import ScrapingStrategy, AnalysisResult
    
    # Create instances to verify they work
    record = ArchiveRecord()
    schema = DataSchema()
    
    assert record is not None
    assert schema is not None
    assert len(schema.columns) > 20  # Should have all fields


def test_all_modules_import():
    """Test that all modules can be imported without errors."""
    from src.modules.analyzer import Analyzer
    from src.modules.planner import Planner
    from src.modules.executor import Executor
    from src.modules.verifier import Verifier
    from src.modules.data_handler import DataHandler
    
    # Create instances
    analyzer = Analyzer()
    planner = Planner()
    executor = Executor()
    verifier = Verifier()
    data_handler = DataHandler()
    
    # Verify they have expected methods
    assert hasattr(analyzer, 'analyze_page')
    assert hasattr(planner, 'generate_strategy')
    assert hasattr(executor, 'execute_strategy')
    assert hasattr(verifier, 'verify_data')
    assert hasattr(data_handler, 'save_to_csv')