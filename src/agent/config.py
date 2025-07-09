"""Configuration and constants for the scraping agent."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AgentConfig(BaseModel):
    """Configuration for the autonomous scraping agent."""
    
    # Browser settings
    headless: bool = Field(default=True, description="Run browser in headless mode")
    browser_timeout: int = Field(default=60000, description="Browser timeout in milliseconds")
    
    # Scraping settings
    max_pages: int = Field(default=100, description="Maximum pages to scrape")
    max_results: int = Field(default=50, description="Maximum number of items to extract")
    max_retries: int = Field(default=3, description="Maximum retries for failed operations")
    retry_delay: int = Field(default=2000, description="Delay between retries in milliseconds")
    
    # Self-correction settings
    enable_self_correction: bool = Field(default=True, description="Enable self-correction loop")
    max_correction_attempts: int = Field(default=2, description="Maximum self-correction attempts")
    min_quality_threshold: float = Field(default=0.6, description="Minimum quality score threshold")
    
    # Data validation settings
    require_critical_fields: bool = Field(default=True, description="Require all critical fields")
    min_completeness_score: float = Field(default=0.5, description="Minimum completeness score")
    
    # Output settings
    output_file: str = Field(default="scraped_data.csv", description="Output CSV filename")
    save_intermediate: bool = Field(default=True, description="Save data after each page")
    
    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    screenshot_on_error: bool = Field(default=True, description="Take screenshot on errors")
    
    model_config = ConfigDict(validate_assignment=True)