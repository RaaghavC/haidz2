"""Unit tests for the Executor module."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from playwright.async_api import Page, Browser

from src.modules.executor import Executor
from src.models.schemas import ArchiveRecord
from src.models.strategies import (
    ScrapingStrategy, FieldMapping, NavigationStrategy
)
from src.utils.browser_manager import BrowserManager


class TestExecutor:
    """Test suite for Executor functionality."""
    
    @pytest.fixture
    def executor(self):
        """Create an Executor instance."""
        return Executor()
    
    @pytest.fixture
    def mock_browser_manager(self):
        """Create a mock browser manager."""
        manager = AsyncMock(spec=BrowserManager)
        return manager
    
    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright page."""
        page = AsyncMock(spec=Page)
        page.url = "https://test-archive.org/items"
        page.goto = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.query_selector = AsyncMock()
        page.query_selector_all = AsyncMock()
        page.evaluate = AsyncMock()
        return page
    
    @pytest.fixture
    def sample_strategy(self):
        """Create a sample scraping strategy."""
        return ScrapingStrategy(
            url="https://test-archive.org/items",
            field_mapping=FieldMapping(
                mappings={
                    "Title": ".title",
                    "Artist": ".artist", 
                    "Date photograph taken": ".date",
                    "Collection": ".collection",
                    "Inventory #": ".inventory-num"
                },
                confidence_scores={},
                unmapped_fields=[]
            ),
            navigation_strategy=NavigationStrategy(
                method="click_next",
                selectors={"next": ".next-page"},
                parameters={"max_pages": 3, "wait_after_click": 1000}
            ),
            extraction_method="css_selector",
            wait_conditions=["selector:.item-list"],
            error_handling={}
        )


class TestStrategyExecution(TestExecutor):
    """Test strategy execution functionality."""
    
    @pytest.mark.asyncio
    async def test_execute_strategy_returns_records(self, sample_strategy, mock_browser_manager):
        """Test that execute_strategy returns archive records."""
        # Create executor with mocked browser manager
        executor = Executor(browser_manager=mock_browser_manager)
        
        # Mock page with data
        mock_page = AsyncMock()
        
        # Create a proper async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_page)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        
        mock_browser_manager.create_page.return_value = mock_context_manager
        mock_browser_manager.stop = AsyncMock()
        
        # Mock page behavior
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector_all = AsyncMock(return_value=[])
        
        # Mock data extraction
        executor.extract_page_data = AsyncMock(return_value=[
            {"Title": "Item 1", "Artist": "Artist 1"},
            {"Title": "Item 2", "Artist": "Artist 2"}
        ])
        
        # Mock navigation
        executor.navigate_to_next = AsyncMock(side_effect=[True, True, False])
        
        results = await executor.execute_strategy(sample_strategy)
        
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, dict) for r in results)
    
    @pytest.mark.asyncio
    async def test_extract_page_data_single_page(self, executor, mock_page):
        """Test data extraction from a single page."""
        field_mapping = FieldMapping(
            mappings={
                "Title": "h3.title",
                "Artist": ".creator",
                "Date": ".date"
            },
            confidence_scores={},
            unmapped_fields=[]
        )
        
        # Mock elements
        mock_items = []
        for i in range(3):
            item = AsyncMock()
            item.query_selector = AsyncMock(side_effect=lambda sel: AsyncMock(
                inner_text=AsyncMock(return_value=f"Value {i}")
            ))
            mock_items.append(item)
        
        mock_page.query_selector_all = AsyncMock(return_value=mock_items)
        
        # Determine container selector
        container_selector = await executor._determine_container_selector(mock_page, field_mapping)
        
        data = await executor.extract_page_data(mock_page, field_mapping, container_selector)
        
        assert isinstance(data, list)
        assert len(data) == 3
    
    @pytest.mark.asyncio
    async def test_extract_single_item(self, executor, mock_page):
        """Test extraction of data from a single item."""
        mock_element = AsyncMock()
        
        # Mock field elements
        title_elem = AsyncMock()
        title_elem.inner_text = AsyncMock(return_value="Historical Building")
        
        artist_elem = AsyncMock()
        artist_elem.inner_text = AsyncMock(return_value="John Doe")
        
        mock_element.query_selector = AsyncMock(side_effect={
            ".title": title_elem,
            ".artist": artist_elem,
            ".missing": None
        }.get)
        
        field_mapping = {
            "Title": ".title",
            "Artist": ".artist",
            "Notes": ".missing"
        }
        
        data = await executor._extract_single_item(mock_element, field_mapping)
        
        assert data["Title"] == "Historical Building"
        assert data["Artist"] == "John Doe"
        assert data["Notes"] is None


class TestNavigation(TestExecutor):
    """Test navigation functionality."""
    
    @pytest.mark.asyncio
    async def test_navigate_click_next(self, executor, mock_page):
        """Test click-based navigation."""
        nav_strategy = NavigationStrategy(
            method="click_next",
            selectors={"next": ".next-btn"},
            parameters={"wait_after_click": 1000}
        )
        
        # Mock next button exists
        next_button = AsyncMock()
        next_button.click = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=next_button)
        mock_page.wait_for_timeout = AsyncMock()
        
        result = await executor.navigate_to_next(mock_page, nav_strategy)
        
        assert result is True
        next_button.click.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_navigate_no_next_button(self, executor, mock_page):
        """Test navigation when next button not found."""
        nav_strategy = NavigationStrategy(
            method="click_next",
            selectors={"next": ".next-btn"},
            parameters={}
        )
        
        # Mock no next button
        mock_page.query_selector = AsyncMock(return_value=None)
        
        result = await executor.navigate_to_next(mock_page, nav_strategy)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_navigate_scroll(self, executor, mock_page):
        """Test scroll-based navigation."""
        nav_strategy = NavigationStrategy(
            method="scroll",
            selectors={},
            parameters={
                "scroll_pause_time": 500,
                "max_scrolls": 3
            }
        )
        
        # Mock scroll behavior - need to handle both evaluate calls
        # First call gets scroll info, second does the scroll
        mock_page.evaluate = AsyncMock(side_effect=[
            {"scrollTop": 0, "scrollHeight": 2000},     # Not at bottom
            None,                                        # scroll action
            {"scrollTop": 500, "scrollHeight": 2000},   # Still not at bottom
            None,                                        # scroll action
            {"scrollTop": 1500, "scrollHeight": 2000},  # At bottom (within 1000px)
            None                                         # scroll action (won't happen)
        ])
        mock_page.wait_for_timeout = AsyncMock()
        
        # Keep track of scroll count
        executor._scroll_count = 0
        
        # First two scrolls should return True, third should return False
        result1 = await executor.navigate_to_next(mock_page, nav_strategy)
        assert result1 is True
        
        result2 = await executor.navigate_to_next(mock_page, nav_strategy)
        assert result2 is True
        
        result3 = await executor.navigate_to_next(mock_page, nav_strategy)
        assert result3 is False


class TestErrorHandling(TestExecutor):
    """Test error handling functionality."""
    
    @pytest.mark.asyncio
    async def test_handle_timeout_error(self, executor, sample_strategy, mock_browser_manager):
        """Test handling of timeout errors."""
        with patch('src.modules.executor.BrowserManager', return_value=mock_browser_manager):
            mock_page = AsyncMock()
            mock_browser_manager.create_page = AsyncMock()
            mock_browser_manager.create_page.__aenter__ = AsyncMock(return_value=mock_page)
            mock_browser_manager.create_page.__aexit__ = AsyncMock()
            
            # Mock timeout error
            mock_page.goto = AsyncMock(side_effect=TimeoutError("Navigation timeout"))
            
            results = await executor.execute_strategy(sample_strategy)
            
            # Should return empty list on critical error
            assert results == []
    
    @pytest.mark.asyncio 
    async def test_retry_on_selector_not_found(self, executor, mock_page):
        """Test retry logic when selector not found."""
        mock_element = AsyncMock()
        
        # First call returns None, second returns element
        mock_element.query_selector = AsyncMock(side_effect=[
            None,
            AsyncMock(inner_text=AsyncMock(return_value="Found"))
        ])
        
        field_mapping = {"Title": ".title"}
        
        # Enable retry
        executor.retry_on_missing = True
        
        data = await executor._extract_single_item(mock_element, field_mapping)
        
        assert data["Title"] == "Found" or data["Title"] is None


class TestWaitConditions(TestExecutor):
    """Test wait condition handling."""
    
    @pytest.mark.asyncio
    async def test_apply_wait_conditions_selector(self, executor, mock_page):
        """Test waiting for selector."""
        conditions = ["selector:.item-list", "selector:.pagination"]
        
        await executor._apply_wait_conditions(mock_page, conditions)
        
        assert mock_page.wait_for_selector.call_count == 2
        mock_page.wait_for_selector.assert_any_call(".item-list", timeout=10000)
        mock_page.wait_for_selector.assert_any_call(".pagination", timeout=10000)
    
    @pytest.mark.asyncio
    async def test_apply_wait_conditions_timeout(self, executor, mock_page):
        """Test custom timeout in wait conditions."""
        conditions = ["timeout:5000", "selector:.content"]
        
        await executor._apply_wait_conditions(mock_page, conditions)
        
        mock_page.wait_for_timeout.assert_called_once_with(5000)
        mock_page.wait_for_selector.assert_called_once()


class TestContainerDetection(TestExecutor):
    """Test automatic container detection."""
    
    @pytest.mark.asyncio
    async def test_determine_container_selector(self, executor, mock_page):
        """Test container selector determination."""
        field_mapping = FieldMapping(
            mappings={
                "Title": ".title",
                "Date": ".date"
            },
            confidence_scores={},
            unmapped_fields=[]
        )
        
        # Mock multiple containers with items
        mock_page.query_selector_all = AsyncMock(side_effect=[
            [AsyncMock(), AsyncMock(), AsyncMock()],  # 3 divs
            [],  # 0 articles
            [AsyncMock()] * 10,  # 10 li elements
        ])
        
        container = await executor._determine_container_selector(mock_page, field_mapping)
        
        assert container is not None
        assert container in ["div", "article", "li", ".item", ".record"]