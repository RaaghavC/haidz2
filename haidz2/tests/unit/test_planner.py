"""Unit tests for the Planner module."""

import pytest
from unittest.mock import Mock, AsyncMock

from src.modules.planner import Planner
from src.models.schemas import DataSchema, ArchiveRecord
from src.models.strategies import (
    AnalysisResult, DataContainer, NavigationPattern,
    ScrapingStrategy, FieldMapping, NavigationStrategy,
    ElementPattern, ElementType
)


class TestPlanner:
    """Test suite for Planner functionality."""
    
    @pytest.fixture
    def planner(self):
        """Create a Planner instance."""
        return Planner()
    
    @pytest.fixture
    def schema(self):
        """Create a DataSchema instance."""
        return DataSchema()
    
    @pytest.fixture
    def sample_analysis_result(self):
        """Create a sample analysis result."""
        return AnalysisResult(
            url="https://test-archive.org/items",
            page_type="listing",
            element_patterns=[
                ElementPattern(
                    selector=".item",
                    element_type=ElementType.DATA_CONTAINER,
                    count=10,
                    confidence=0.9
                )
            ],
            data_containers=[
                DataContainer(
                    selector=".item-list",
                    item_selector=".item",
                    field_selectors={
                        "title": ".title",
                        "creator": ".artist",
                        "date": ".date-created",
                        "link": "a.detail-link"
                    },
                    sample_data=[
                        {
                            "title": "Historical Building 1",
                            "creator": "John Doe",
                            "date": "1950",
                            "link": "/item/1"
                        }
                    ],
                    confidence=0.85
                )
            ],
            navigation_pattern=NavigationPattern(
                type="pagination",
                next_selector=".next-page",
                pagination_selector=".pagination",
                total_pages=5,
                current_page=1
            ),
            confidence=0.87
        )


class TestStrategyGeneration(TestPlanner):
    """Test strategy generation functionality."""
    
    def test_generate_strategy_returns_scraping_strategy(self, planner, sample_analysis_result, schema):
        """Test that generate_strategy returns a ScrapingStrategy."""
        strategy = planner.generate_strategy(sample_analysis_result, schema)
        
        assert isinstance(strategy, ScrapingStrategy)
        assert strategy.url == "https://test-archive.org/items"
        assert isinstance(strategy.field_mapping, FieldMapping)
        assert isinstance(strategy.navigation_strategy, NavigationStrategy)
    
    def test_generate_strategy_with_high_confidence_container(self, planner, sample_analysis_result, schema):
        """Test strategy generation with high confidence data container."""
        strategy = planner.generate_strategy(sample_analysis_result, schema)
        
        # Should use the high confidence container
        assert len(strategy.field_mapping.mappings) > 0
        assert "Title" in strategy.field_mapping.mappings
        assert strategy.field_mapping.mappings["Title"] == ".title"
    
    def test_generate_strategy_without_containers(self, planner, schema):
        """Test strategy generation when no containers found."""
        analysis = AnalysisResult(
            url="https://test-archive.org/items",
            page_type="unknown",
            element_patterns=[],
            data_containers=[],
            navigation_pattern=None,
            confidence=0.3
        )
        
        strategy = planner.generate_strategy(analysis, schema)
        
        # Should still return a strategy, but with empty mappings
        assert isinstance(strategy, ScrapingStrategy)
        assert len(strategy.field_mapping.mappings) == 0
        assert len(strategy.field_mapping.unmapped_fields) > 0


class TestFieldMapping(TestPlanner):
    """Test field mapping functionality."""
    
    def test_map_fields_to_selectors(self, planner, schema):
        """Test mapping schema fields to CSS selectors."""
        containers = [
            DataContainer(
                selector=".items",
                item_selector=".item",
                field_selectors={
                    "title": "h3.title",
                    "creator": ".photographer",
                    "date": ".creation-date",
                    "description": ".desc"
                },
                sample_data=[],
                confidence=0.9
            )
        ]
        
        mapping = planner.map_fields_to_selectors(containers, schema)
        
        assert isinstance(mapping, FieldMapping)
        assert "Title" in mapping.mappings
        assert "Photographer" in mapping.mappings
        assert mapping.mappings["Title"] == "h3.title"
        assert mapping.mappings["Photographer"] == ".photographer"
    
    def test_semantic_field_matching(self, planner):
        """Test semantic matching of field names."""
        # Test exact matches
        assert planner._match_field_semantically("title", "Title") > 0.8
        assert planner._match_field_semantically("photographer", "Photographer") > 0.8
        
        # Test similar fields
        assert planner._match_field_semantically("creator", "Artist") > 0.6
        assert planner._match_field_semantically("date", "Date photograph taken") > 0.5
        
        # Test unrelated fields
        assert planner._match_field_semantically("price", "Photographer") < 0.4
    
    def test_unmapped_fields_detection(self, planner, schema):
        """Test detection of unmapped required fields."""
        containers = [
            DataContainer(
                selector=".items",
                item_selector=".item",
                field_selectors={
                    "title": "h3",
                    "date": ".date"
                },
                sample_data=[],
                confidence=0.9
            )
        ]
        
        mapping = planner.map_fields_to_selectors(containers, schema)
        
        # Most fields should be unmapped
        assert len(mapping.unmapped_fields) >= 14
        assert "Photographer" in mapping.unmapped_fields
        assert "Collection" in mapping.unmapped_fields


class TestNavigationStrategy(TestPlanner):
    """Test navigation strategy determination."""
    
    def test_determine_pagination_navigation(self, planner):
        """Test navigation strategy for pagination."""
        nav_pattern = NavigationPattern(
            type="pagination",
            next_selector=".next-btn",
            pagination_selector=".pages",
            total_pages=10
        )
        
        strategy = planner.determine_navigation_approach(nav_pattern)
        
        assert strategy.method == "click_next"
        assert strategy.selectors["next"] == ".next-btn"
        assert strategy.parameters["max_pages"] == 10
    
    def test_determine_infinite_scroll_navigation(self, planner):
        """Test navigation strategy for infinite scroll."""
        nav_pattern = NavigationPattern(
            type="infinite_scroll",
            next_selector=None,
            pagination_selector=None
        )
        
        strategy = planner.determine_navigation_approach(nav_pattern)
        
        assert strategy.method == "scroll"
        assert "scroll_pause_time" in strategy.parameters
    
    def test_no_navigation_pattern(self, planner):
        """Test when no navigation pattern exists."""
        strategy = planner.determine_navigation_approach(None)
        
        assert strategy.method == "none"
        assert len(strategy.selectors) == 0


class TestConfidenceScoring(TestPlanner):
    """Test confidence scoring for mappings."""
    
    def test_calculate_mapping_confidence(self, planner):
        """Test confidence calculation for field mappings."""
        # High confidence: many fields mapped
        mapping1 = FieldMapping(
            mappings={"Title": ".title", "Artist": ".artist", "Date": ".date"},
            confidence_scores={"Title": 0.9, "Artist": 0.8, "Date": 0.85},
            unmapped_fields=["Notes"]
        )
        confidence1 = planner._calculate_mapping_confidence(mapping1, total_fields=4)
        assert confidence1 > 0.7
        
        # Low confidence: few fields mapped
        mapping2 = FieldMapping(
            mappings={"Title": ".title"},
            confidence_scores={"Title": 0.9},
            unmapped_fields=["Artist", "Date", "Notes"]
        )
        confidence2 = planner._calculate_mapping_confidence(mapping2, total_fields=4)
        assert confidence2 < 0.6
    
    def test_prioritize_containers_by_confidence(self, planner):
        """Test that containers are prioritized by confidence."""
        containers = [
            DataContainer(selector=".low", item_selector=".item", 
                         field_selectors={}, sample_data=[], confidence=0.3),
            DataContainer(selector=".high", item_selector=".item", 
                         field_selectors={"title": ".title"}, sample_data=[], confidence=0.9),
            DataContainer(selector=".medium", item_selector=".item", 
                         field_selectors={}, sample_data=[], confidence=0.6),
        ]
        
        prioritized = planner._prioritize_containers(containers)
        
        assert prioritized[0].selector == ".high"
        assert prioritized[1].selector == ".medium"
        assert prioritized[2].selector == ".low"