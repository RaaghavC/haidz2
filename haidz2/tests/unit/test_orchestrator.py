"""Unit tests for the Agent orchestrator."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import List, Dict

from src.agent.orchestrator import AutonomousScrapingAgent
from src.agent.config import AgentConfig
from src.models.schemas import DataSchema, ArchiveRecord
from src.models.strategies import (
    AnalysisResult, ScrapingStrategy, VerificationResult,
    ElementPattern, DataContainer, NavigationPattern
)


class TestOrchestrator:
    """Test suite for the Agent orchestrator."""
    
    @pytest.fixture
    def config(self):
        """Create agent configuration."""
        return AgentConfig(
            headless=True,
            max_pages=5,
            enable_self_correction=True,
            max_correction_attempts=2
        )
    
    @pytest.fixture
    def agent(self, config):
        """Create an agent instance."""
        return AutonomousScrapingAgent(
            target_url="https://test-archive.org",
            config=config
        )
    
    @pytest.fixture
    def mock_modules(self):
        """Create mocked modules."""
        return {
            "analyzer": AsyncMock(),
            "planner": Mock(),
            "executor": AsyncMock(),
            "verifier": Mock(),
            "data_handler": Mock()
        }
    
    @pytest.fixture
    def sample_analysis_result(self):
        """Create sample analysis result."""
        return AnalysisResult(
            url="https://test-archive.org",
            page_type="listing",
            element_patterns=[],
            data_containers=[
                DataContainer(
                    selector=".items",
                    item_selector=".item",
                    field_selectors={"title": ".title"},
                    sample_data=[],
                    confidence=0.8
                )
            ],
            navigation_pattern=NavigationPattern(
                type="pagination",
                next_selector=".next"
            ),
            confidence=0.8
        )


class TestCognitiveLoop(TestOrchestrator):
    """Test the cognitive loop implementation."""
    
    @pytest.mark.asyncio
    @patch('src.agent.orchestrator.BrowserManager')
    async def test_run_executes_cognitive_loop(self, mock_browser_manager_class, agent, mock_modules):
        """Test that run method executes the full cognitive loop."""
        # Inject mocked modules
        agent.analyzer = mock_modules["analyzer"]
        agent.planner = mock_modules["planner"]
        agent.executor = mock_modules["executor"]
        agent.verifier = mock_modules["verifier"]
        agent.data_handler = mock_modules["data_handler"]
        
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager_class.return_value = mock_browser_manager
        
        # Mock page
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        
        # Create async context manager mock
        async def create_page_mock(*args, **kwargs):
            class AsyncContextManager:
                async def __aenter__(self):
                    return mock_page
                async def __aexit__(self, *args):
                    pass
            return AsyncContextManager()
        
        mock_browser_manager.create_page = create_page_mock
        mock_browser_manager.stop = AsyncMock()
        
        # Mock analysis phase
        mock_modules["analyzer"].analyze_page.return_value = AnalysisResult(
            url="https://test-archive.org",
            page_type="listing",
            element_patterns=[],
            data_containers=[],
            confidence=0.8
        )
        
        # Mock planning phase
        mock_modules["planner"].generate_strategy.return_value = Mock()
        
        # Mock execution phase
        mock_modules["executor"].execute_strategy.return_value = [
            {"Title": "Item 1", "Collection": "Test", "Inventory #": "001"}
        ]
        
        # Mock verification phase
        mock_modules["verifier"].verify_data.return_value = VerificationResult(
            is_valid=True,
            completeness_score=0.8,
            quality_score=0.9,
            missing_fields=[],
            invalid_records=[],
            error_messages=[],
            recommendations=[]
        )
        
        # Run the agent
        await agent.run()
        
        # Verify all phases were called
        mock_modules["analyzer"].analyze_page.assert_called()
        mock_modules["planner"].generate_strategy.assert_called()
        mock_modules["executor"].execute_strategy.assert_called()
        mock_modules["verifier"].verify_data.assert_called()
        mock_modules["data_handler"].save_to_csv.assert_called()
    
    @pytest.mark.asyncio
    async def test_analyze_phase(self, agent, sample_analysis_result):
        """Test the analyze phase."""
        agent.analyzer = AsyncMock()
        agent.analyzer.analyze_page.return_value = sample_analysis_result
        
        # Create mock page
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        
        result = await agent._analyze_phase(mock_page)
        
        assert result == sample_analysis_result
        agent.analyzer.analyze_page.assert_called_once_with(mock_page)
    
    def test_planning_phase(self, agent, sample_analysis_result):
        """Test the planning phase."""
        agent.planner = Mock()
        expected_strategy = Mock()
        agent.planner.generate_strategy.return_value = expected_strategy
        
        strategy = agent._planning_phase(sample_analysis_result)
        
        assert strategy == expected_strategy
        agent.planner.generate_strategy.assert_called_once()


class TestSelfCorrection(TestOrchestrator):
    """Test self-correction functionality."""
    
    @pytest.mark.asyncio
    async def test_self_correct_on_invalid_data(self, agent, mock_modules):
        """Test self-correction when data is invalid."""
        agent.analyzer = mock_modules["analyzer"]
        agent.planner = mock_modules["planner"]
        agent.executor = mock_modules["executor"]
        agent.verifier = mock_modules["verifier"]
        agent.data_handler = mock_modules["data_handler"]
        
        with patch('src.agent.orchestrator.BrowserManager') as mock_browser_manager_class:
            mock_browser_manager = AsyncMock()
            mock_browser_manager_class.return_value = mock_browser_manager
            
            mock_page = AsyncMock()
            mock_page.goto = AsyncMock()
            
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_page)
            mock_context.__aexit__ = AsyncMock()
            
            mock_browser_manager.create_page = mock_context
            mock_browser_manager.stop = AsyncMock()
        
            # First attempt: invalid data
            mock_modules["verifier"].verify_data.side_effect = [
            VerificationResult(
                is_valid=False,
                completeness_score=0.3,
                quality_score=0.4,
                missing_fields=["Title"],
                invalid_records=[0, 1],
                error_messages=["Missing critical fields"],
                recommendations=["Adjust selectors"]
            ),
            # Second attempt: valid data
            VerificationResult(
                is_valid=True,
                completeness_score=0.8,
                quality_score=0.9,
                missing_fields=[],
                invalid_records=[],
                error_messages=[],
                recommendations=[]
            )
        ]
        
            # Mock other phases
            mock_modules["analyzer"].analyze_page.return_value = Mock(confidence=0.8)
            mock_modules["planner"].generate_strategy.return_value = Mock()
            mock_modules["executor"].execute_strategy.return_value = [{"Title": "Test"}]
            
            await agent.run()
            
            # Should have attempted correction
            assert mock_modules["analyzer"].analyze_page.call_count >= 2
            assert mock_modules["planner"].generate_strategy.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_max_correction_attempts(self, agent, mock_modules):
        """Test that correction attempts are limited."""
        agent.config.max_correction_attempts = 2
        agent.analyzer = mock_modules["analyzer"]
        agent.planner = mock_modules["planner"]
        agent.executor = mock_modules["executor"]
        agent.verifier = mock_modules["verifier"]
        agent.data_handler = mock_modules["data_handler"]
        
        # Always return invalid data
        mock_modules["verifier"].verify_data.return_value = VerificationResult(
            is_valid=False,
            completeness_score=0.3,
            quality_score=0.4,
            missing_fields=["Title"],
            invalid_records=[],
            error_messages=[],
            recommendations=[]
        )
        
        # Mock other phases
        mock_modules["analyzer"].analyze_page.return_value = Mock(confidence=0.8)
        mock_modules["planner"].generate_strategy.return_value = Mock()
        mock_modules["executor"].execute_strategy.return_value = []
        
        await agent.run()
        
        # Should stop after max attempts (1 initial + 2 corrections = 3 total)
        assert mock_modules["analyzer"].analyze_page.call_count <= 3


class TestErrorHandling(TestOrchestrator):
    """Test error handling in the orchestrator."""
    
    @pytest.mark.asyncio
    async def test_handle_analyzer_error(self, agent, mock_modules):
        """Test handling of analyzer errors."""
        agent.analyzer = mock_modules["analyzer"]
        agent.data_handler = mock_modules["data_handler"]
        
        # Mock analyzer to raise error
        mock_modules["analyzer"].analyze_page.side_effect = Exception("Analysis failed")
        
        # Should not crash
        await agent.run()
        
        # Should save empty data
        mock_modules["data_handler"].save_to_csv.assert_called_with([], agent.config.output_file)
    
    @pytest.mark.asyncio
    async def test_handle_executor_error(self, agent, mock_modules):
        """Test handling of executor errors."""
        agent.analyzer = mock_modules["analyzer"]
        agent.planner = mock_modules["planner"]
        agent.executor = mock_modules["executor"]
        agent.data_handler = mock_modules["data_handler"]
        
        # Mock successful analysis and planning
        mock_modules["analyzer"].analyze_page.return_value = Mock(confidence=0.8)
        mock_modules["planner"].generate_strategy.return_value = Mock()
        
        # Mock executor to raise error
        mock_modules["executor"].execute_strategy.side_effect = Exception("Execution failed")
        
        await agent.run()
        
        # Should save empty data
        mock_modules["data_handler"].save_to_csv.assert_called_with([], agent.config.output_file)


class TestDataPersistence(TestOrchestrator):
    """Test data persistence functionality."""
    
    @pytest.mark.asyncio
    async def test_save_intermediate_data(self, agent, mock_modules):
        """Test saving intermediate data when enabled."""
        agent.config.save_intermediate = True
        agent.analyzer = mock_modules["analyzer"]
        agent.planner = mock_modules["planner"]
        agent.executor = mock_modules["executor"]
        agent.verifier = mock_modules["verifier"]
        agent.data_handler = mock_modules["data_handler"]
        
        with patch('src.agent.orchestrator.BrowserManager') as mock_browser_manager_class:
            mock_browser_manager = AsyncMock()
            mock_browser_manager_class.return_value = mock_browser_manager
            
            mock_page = AsyncMock()
            mock_page.goto = AsyncMock()
            
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_page)
            mock_context.__aexit__ = AsyncMock()
            
            mock_browser_manager.create_page = mock_context
            mock_browser_manager.stop = AsyncMock()
        
            # Mock successful execution
            mock_modules["analyzer"].analyze_page.return_value = Mock(confidence=0.8)
            mock_modules["planner"].generate_strategy.return_value = Mock()
            mock_modules["executor"].execute_strategy.return_value = [
                {"Title": "Item 1"},
                {"Title": "Item 2"}
            ]
            mock_modules["verifier"].verify_data.return_value = VerificationResult(
                is_valid=True,
                completeness_score=0.8,
                quality_score=0.9,
                missing_fields=[],
                invalid_records=[],
                error_messages=[],
                recommendations=[]
            )
            
            await agent.run()
            
            # Should save data
            mock_modules["data_handler"].save_to_csv.assert_called()
            saved_data = mock_modules["data_handler"].save_to_csv.call_args[0][0]
            assert len(saved_data) == 2