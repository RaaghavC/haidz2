"""Strategy and analysis result models for the scraping agent."""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class ElementType(str, Enum):
    """Types of elements that can be identified."""
    DATA_CONTAINER = "data_container"
    NAVIGATION = "navigation"
    PAGINATION = "pagination"
    DETAIL_LINK = "detail_link"
    METADATA = "metadata"


class ElementPattern(BaseModel):
    """Represents a pattern found in the DOM."""
    selector: str = Field(..., description="CSS selector for the element")
    element_type: ElementType
    count: int = Field(..., description="Number of occurrences found")
    attributes: Dict[str, Any] = Field(default_factory=dict)
    sample_text: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


class DataContainer(BaseModel):
    """Represents a container that holds data records."""
    selector: str
    item_selector: str = Field(..., description="Selector for individual items within container")
    field_selectors: Dict[str, str] = Field(default_factory=dict, description="Map of field names to selectors")
    sample_data: List[Dict[str, str]] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)


class NavigationPattern(BaseModel):
    """Represents navigation patterns found on the page."""
    type: str = Field(..., description="Type of navigation: pagination, infinite_scroll, etc.")
    next_selector: Optional[str] = None
    pagination_selector: Optional[str] = None
    total_pages: Optional[int] = None
    current_page: Optional[int] = None


class AnalysisResult(BaseModel):
    """Complete result of page analysis."""
    url: str
    page_type: str = Field(..., description="Type of page: listing, detail, etc.")
    element_patterns: List[ElementPattern]
    data_containers: List[DataContainer]
    navigation_pattern: Optional[NavigationPattern] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(..., ge=0.0, le=1.0)


class FieldMapping(BaseModel):
    """Maps schema fields to DOM selectors."""
    mappings: Dict[str, str] = Field(..., description="Map of schema field to CSS selector")
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    unmapped_fields: List[str] = Field(default_factory=list)


class NavigationStrategy(BaseModel):
    """Strategy for navigating through pages."""
    method: str = Field(..., description="Navigation method: click_next, pagination, scroll")
    selectors: Dict[str, str] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ScrapingStrategy(BaseModel):
    """Complete strategy for scraping a website."""
    url: str
    field_mapping: FieldMapping
    navigation_strategy: NavigationStrategy
    container_selector: Optional[str] = None
    item_selector: Optional[str] = None
    extraction_method: str = Field(default="css_selector")
    wait_conditions: List[str] = Field(default_factory=list)
    error_handling: Dict[str, str] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    """Result of data verification."""
    is_valid: bool
    completeness_score: float = Field(..., ge=0.0, le=1.0)
    quality_score: float = Field(..., ge=0.0, le=1.0)
    missing_fields: List[str] = Field(default_factory=list)
    invalid_records: List[int] = Field(default_factory=list)
    error_messages: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)