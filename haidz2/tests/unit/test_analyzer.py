"""Unit tests for the Analyzer module."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from playwright.async_api import Page, ElementHandle

from src.modules.analyzer import Analyzer
from src.models.strategies import (
    AnalysisResult, ElementPattern, DataContainer, 
    NavigationPattern, ElementType
)


class TestAnalyzer:
    """Test suite for Analyzer functionality."""
    
    @pytest.fixture
    def analyzer(self):
        """Create an Analyzer instance."""
        return Analyzer()
    
    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright page."""
        page = AsyncMock(spec=Page)
        page.url = "https://test-archive.org/items"
        page.title = AsyncMock(return_value="Test Page")
        page.content = AsyncMock(return_value="")
        page.query_selector = AsyncMock(return_value=None)
        page.query_selector_all = AsyncMock(return_value=[])
        return page
    
    @pytest.fixture
    def sample_html(self):
        """Sample HTML content for testing."""
        return """
        <html>
            <body>
                <div class="item-list">
                    <div class="item">
                        <h3 class="title">Item 1</h3>
                        <span class="creator">Artist 1</span>
                        <span class="date">1950</span>
                        <a href="/item/1" class="detail-link">View Details</a>
                    </div>
                    <div class="item">
                        <h3 class="title">Item 2</h3>
                        <span class="creator">Artist 2</span>
                        <span class="date">1960</span>
                        <a href="/item/2" class="detail-link">View Details</a>
                    </div>
                    <div class="item">
                        <h3 class="title">Item 3</h3>
                        <span class="creator">Artist 3</span>
                        <span class="date">1970</span>
                        <a href="/item/3" class="detail-link">View Details</a>
                    </div>
                </div>
                <div class="pagination">
                    <a href="?page=1" class="page-link">1</a>
                    <a href="?page=2" class="page-link current">2</a>
                    <a href="?page=3" class="page-link">3</a>
                    <a href="?page=3" class="next-page">Next</a>
                </div>
            </body>
        </html>
        """


class TestPageAnalysis(TestAnalyzer):
    """Test page analysis functionality."""
    
    @pytest.mark.asyncio
    async def test_analyze_page_returns_analysis_result(self, analyzer, mock_page):
        """Test that analyze_page returns an AnalysisResult."""
        result = await analyzer.analyze_page(mock_page)
        
        assert isinstance(result, AnalysisResult)
        assert result.url == "https://test-archive.org/items"
        assert result.page_type in ["listing", "detail", "unknown"]
        assert isinstance(result.element_patterns, list)
        assert isinstance(result.data_containers, list)
    
    @pytest.mark.asyncio
    async def test_identify_repeating_elements(self, analyzer, mock_page, sample_html):
        """Test identification of repeating elements."""
        mock_page.content.return_value = sample_html
        
        # Create proper mock elements with inner_text
        mock_elements = []
        for i in range(3):
            elem = AsyncMock()
            elem.inner_text = AsyncMock(return_value=f"Item {i} text")
            mock_elements.append(elem)
        
        mock_page.query_selector_all.return_value = mock_elements
        
        patterns = await analyzer.identify_repeating_elements(mock_page)
        
        assert len(patterns) > 0
        # Should identify the .item pattern
        item_pattern = next((p for p in patterns if ".item" in p.selector), None)
        assert item_pattern is not None
        assert item_pattern.count == 3
        assert item_pattern.element_type == ElementType.DATA_CONTAINER
    
    @pytest.mark.asyncio
    async def test_detect_data_containers(self, analyzer, mock_page, sample_html):
        """Test detection of data containers."""
        mock_page.content.return_value = sample_html
        
        # Mock container element
        mock_container = AsyncMock()
        
        # Mock items within container
        mock_items = []
        for i in range(3):
            item = AsyncMock()
            # Set up query_selector to return mock elements for different selectors
            async def make_query_selector(idx):
                async def query_selector(sel):
                    mock_elem = AsyncMock()
                    mock_elem.inner_text = AsyncMock(return_value=f"Text {idx}")
                    mock_elem.get_attribute = AsyncMock(return_value=f"/item/{idx}")
                    return mock_elem
                return query_selector
            
            item.query_selector = await make_query_selector(i)
            mock_items.append(item)
        
        # Set up container to return items
        mock_container.query_selector_all = AsyncMock(return_value=mock_items)
        
        # Set up page to return container
        mock_page.query_selector = AsyncMock(return_value=mock_container)
        
        containers = await analyzer.detect_data_containers(mock_page)
        
        assert len(containers) > 0
        # Should detect the item-list container
        container = containers[0]
        assert container.selector == ".item-list"
        assert container.item_selector == ".item"
        assert len(container.field_selectors) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_navigation_patterns(self, analyzer, mock_page, sample_html):
        """Test navigation pattern analysis."""
        mock_page.content.return_value = sample_html
        
        # Mock pagination elements
        mock_page.query_selector.return_value = AsyncMock()  # pagination div exists
        mock_page.query_selector_all.return_value = [
            AsyncMock(), AsyncMock(), AsyncMock()  # 3 page links
        ]
        
        nav_pattern = await analyzer.analyze_navigation_patterns(mock_page)
        
        assert nav_pattern is not None
        assert nav_pattern.type == "pagination"
        assert nav_pattern.next_selector == ".next-page"
        assert nav_pattern.current_page == 2
    
    @pytest.mark.asyncio
    async def test_analyze_detail_page(self, analyzer, mock_page):
        """Test analysis of a detail page."""
        detail_html = """
        <html>
            <body>
                <div class="detail-container">
                    <h1 class="title">Historical Building</h1>
                    <div class="metadata">
                        <span class="label">Photographer:</span>
                        <span class="value">John Doe</span>
                    </div>
                    <div class="metadata">
                        <span class="label">Date:</span>
                        <span class="value">1950-01-01</span>
                    </div>
                    <img src="/image.jpg" class="main-image">
                </div>
            </body>
        </html>
        """
        
        mock_page.content.return_value = detail_html
        mock_page.url = "https://test-archive.org/item/123"
        
        result = await analyzer.analyze_page(mock_page)
        
        assert result.page_type == "detail"
        assert len(result.element_patterns) > 0
        
        # Should identify metadata patterns
        metadata_pattern = next(
            (p for p in result.element_patterns if p.element_type == ElementType.METADATA),
            None
        )
        assert metadata_pattern is not None


class TestPatternRecognition(TestAnalyzer):
    """Test pattern recognition functionality."""
    
    @pytest.mark.asyncio
    async def test_calculate_element_confidence(self, analyzer):
        """Test confidence calculation for elements."""
        # Elements with consistent structure should have high confidence
        consistent_elements = [
            {"class": "item", "children": 3},
            {"class": "item", "children": 3},
            {"class": "item", "children": 3},
        ]
        
        confidence = analyzer._calculate_pattern_confidence(consistent_elements)
        assert confidence > 0.8
        
        # Elements with inconsistent structure should have lower confidence
        inconsistent_elements = [
            {"class": "item", "children": 3},
            {"class": "item", "children": 1},
            {"class": "item", "children": 5},
        ]
        
        confidence = analyzer._calculate_pattern_confidence(inconsistent_elements)
        assert confidence < 0.6
    
    @pytest.mark.asyncio
    async def test_extract_field_selectors(self, analyzer, mock_page):
        """Test extraction of field selectors from a container."""
        container_html = """
        <div class="item">
            <h3 class="title">Test Title</h3>
            <span class="creator">Test Creator</span>
            <span class="date">2023</span>
            <div class="description">Test description</div>
        </div>
        """
        
        mock_element = AsyncMock()
        mock_element.inner_html.return_value = container_html
        
        selectors = await analyzer._extract_field_selectors(mock_element)
        
        assert ".title" in selectors.values()
        assert ".creator" in selectors.values()
        assert ".date" in selectors.values()
        assert len(selectors) >= 3
    
    @pytest.mark.asyncio
    async def test_detect_pagination_type(self, analyzer, mock_page):
        """Test detection of different pagination types."""
        # Test numbered pagination
        numbered_html = """
        <div class="pagination">
            <a href="?page=1">1</a>
            <a href="?page=2" class="current">2</a>
            <a href="?page=3">3</a>
        </div>
        """
        mock_page.content.return_value = numbered_html
        result = await analyzer._detect_pagination_type(mock_page)
        assert result == "numbered"
        
        # Test next/prev pagination
        nextprev_html = """
        <div class="navigation">
            <a href="?page=1" class="prev">Previous</a>
            <a href="?page=3" class="next">Next</a>
        </div>
        """
        mock_page.content.return_value = nextprev_html
        result = await analyzer._detect_pagination_type(mock_page)
        assert result == "next_prev"
        
        # Test infinite scroll
        infinite_html = """
        <div class="items" data-infinite-scroll="true">
            <div class="item">Item 1</div>
            <div class="load-more">Loading...</div>
        </div>
        """
        mock_page.content.return_value = infinite_html
        result = await analyzer._detect_pagination_type(mock_page)
        assert result == "infinite_scroll"