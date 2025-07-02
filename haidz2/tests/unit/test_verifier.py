"""Unit tests for the Verifier module."""

import pytest
from typing import List, Dict

from src.modules.verifier import Verifier
from src.models.schemas import DataSchema, ArchiveRecord
from src.models.strategies import VerificationResult


class TestVerifier:
    """Test suite for Verifier functionality."""
    
    @pytest.fixture
    def verifier(self):
        """Create a Verifier instance."""
        return Verifier()
    
    @pytest.fixture
    def schema(self):
        """Create a DataSchema instance."""
        return DataSchema()
    
    @pytest.fixture
    def sample_data(self):
        """Create sample scraped data."""
        return [
            {
                "Title": "Historical Building 1",
                "Artist": "John Doe",
                "Photographer": "Jane Smith",
                "Date photograph taken": "1950-01-01",
                "Collection": "Library of Congress",
                "Inventory #": "LC-12345"
            },
            {
                "Title": "Ancient Temple",
                "Artist": None,
                "Photographer": "Unknown",
                "Date photograph taken": "1960",
                "Collection": "MIT Archives",
                "Inventory #": "MIT-67890"
            },
            {
                "Title": None,  # Missing required field
                "Artist": "Anonymous",
                "Photographer": None,
                "Date photograph taken": None,
                "Collection": "Harvard",
                "Inventory #": None
            }
        ]


class TestDataVerification(TestVerifier):
    """Test data verification functionality."""
    
    def test_verify_data_returns_verification_result(self, verifier, sample_data, schema):
        """Test that verify_data returns a VerificationResult."""
        result = verifier.verify_data(sample_data, schema)
        
        assert isinstance(result, VerificationResult)
        assert isinstance(result.is_valid, bool)
        assert 0 <= result.completeness_score <= 1
        assert 0 <= result.quality_score <= 1
    
    def test_verify_complete_data(self, verifier, schema):
        """Test verification of complete, high-quality data."""
        complete_data = [
            {
                "Title": "Building A",
                "Photographer": "John Doe",
                "Collection": "Archive X",
                "Inventory #": "X-001",
                "Date photograph taken": "2023-01-01",
                "Artist": "Artist A"
            }
        ]
        
        result = verifier.verify_data(complete_data, schema)
        
        # Data has 6 fields out of ~22, so completeness will be low
        # but quality should be high
        assert result.quality_score > 0.8
        assert result.completeness_score < 0.5  # Low coverage expected
        assert len(result.missing_fields) == 0
        assert len(result.invalid_records) == 0
    
    def test_verify_incomplete_data(self, verifier, sample_data, schema):
        """Test verification of incomplete data."""
        result = verifier.verify_data(sample_data, schema)
        
        # Third record has missing title, should be invalid
        assert 2 in result.invalid_records
        assert len(result.missing_fields) > 0


class TestFieldValidation(TestVerifier):
    """Test field validation functionality."""
    
    def test_check_required_fields(self, verifier, schema):
        """Test checking for required fields."""
        record = {
            "Title": None,
            "Collection": "Test Archive",
            "Artist": "Test Artist"
        }
        
        missing = verifier.check_required_fields(record, schema)
        
        assert "Title" in missing
        assert "Inventory #" in missing
    
    def test_identify_critical_fields(self, verifier):
        """Test identification of critical fields."""
        critical = verifier._get_critical_fields()
        
        assert "Title" in critical
        assert "Collection" in critical
        assert "Inventory #" in critical
    
    def test_validate_data_types(self, verifier, schema):
        """Test data type validation."""
        record = {
            "Title": "Valid Title",
            "Date photograph taken": "invalid-date",
            "Inventory #": 12345,  # Should be string
            "Artist": "Valid Artist"
        }
        
        issues = verifier.validate_data_types(record, schema)
        
        assert len(issues) > 0
        assert any("Date" in issue for issue in issues)


class TestQualityAssessment(TestVerifier):
    """Test data quality assessment."""
    
    def test_assess_extraction_quality_high(self, verifier):
        """Test quality assessment for well-extracted data."""
        high_quality_data = [
            {
                "Title": "Clear Title with Good Detail",
                "Artist": "John Doe",
                "Date photograph taken": "1950-05-15",
                "Collection": "National Archives",
                "Inventory #": "NA-2023-001",
                "Photographer": "Jane Smith"
            }
        ]
        
        quality = verifier.assess_extraction_quality(high_quality_data)
        
        assert quality > 0.7
    
    def test_assess_extraction_quality_low(self, verifier):
        """Test quality assessment for poorly extracted data."""
        low_quality_data = [
            {
                "Title": "...",
                "Artist": "Unknown",
                "Date photograph taken": None,
                "Collection": "N/A",
                "Inventory #": "",
                "Photographer": None
            }
        ]
        
        quality = verifier.assess_extraction_quality(low_quality_data)
        
        assert quality < 0.5
    
    def test_calculate_field_quality(self, verifier):
        """Test individual field quality calculation."""
        # Good quality field
        assert verifier._calculate_field_quality("Title", "Historical Building in Cairo") > 0.8
        
        # Poor quality fields
        assert verifier._calculate_field_quality("Title", "...") < 0.3
        assert verifier._calculate_field_quality("Artist", "Unknown") < 0.5
        assert verifier._calculate_field_quality("Date", "N/A") < 0.3


class TestRecommendations(TestVerifier):
    """Test recommendation generation."""
    
    def test_generate_recommendations_missing_critical(self, verifier, schema):
        """Test recommendations when critical fields are missing."""
        data = [
            {"Artist": "John Doe", "Date photograph taken": "1950"}
        ]
        
        result = verifier.verify_data(data, schema)
        
        assert len(result.recommendations) > 0
        assert any("Title" in rec for rec in result.recommendations)
        assert any("critical" in rec.lower() for rec in result.recommendations)
    
    def test_generate_recommendations_low_quality(self, verifier, schema):
        """Test recommendations for low quality data."""
        data = [
            {
                "Title": "...",
                "Collection": "Unknown",
                "Inventory #": "N/A"
            }
        ]
        
        result = verifier.verify_data(data, schema)
        
        assert len(result.recommendations) > 0
        assert any("quality" in rec.lower() for rec in result.recommendations)
    
    def test_generate_recommendations_improve_coverage(self, verifier, schema):
        """Test recommendations to improve field coverage."""
        data = [
            {
                "Title": "Good Title",
                "Collection": "Good Collection",
                "Inventory #": "123"
                # Missing many optional fields
            }
        ]
        
        result = verifier.verify_data(data, schema)
        
        assert any("coverage" in rec.lower() or "additional" in rec.lower() 
                   for rec in result.recommendations)


class TestEdgeCases(TestVerifier):
    """Test edge cases and error handling."""
    
    def test_verify_empty_data(self, verifier, schema):
        """Test verification of empty data."""
        result = verifier.verify_data([], schema)
        
        assert result.is_valid is False
        assert result.completeness_score == 0
        assert "No data" in result.error_messages[0]
    
    def test_verify_malformed_data(self, verifier, schema):
        """Test verification of malformed data."""
        malformed_data = [
            "not a dict",
            {"Title": "Valid"},
            None,
            {"Title": "Another Valid"}
        ]
        
        result = verifier.verify_data(malformed_data, schema)
        
        assert result.is_valid is False
        assert len(result.invalid_records) > 0
        assert len(result.error_messages) > 0