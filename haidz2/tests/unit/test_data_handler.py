"""Unit tests for the DataHandler module."""

import pytest
from pathlib import Path
import pandas as pd
import tempfile
import shutil

from src.modules.data_handler import DataHandler
from src.models.schemas import ArchiveRecord, DataSchema, UniqueIDMappings


class TestDataHandler:
    """Test suite for DataHandler functionality."""
    
    @pytest.fixture
    def data_handler(self):
        """Create a DataHandler instance."""
        return DataHandler()
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for file operations."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def sample_records(self):
        """Create sample archive records for testing."""
        return [
            ArchiveRecord(
                typ="Modern Photo",
                title="Mosque Interior View",
                photographer="Patricia Blessing",
                collection="Library of Congress",
                inventory_num="LC-12345",
                artist="Unknown",
                orig_location="Istanbul, Turkey"
            ),
            ArchiveRecord(
                typ="Historical Image",
                title="Ancient Temple Ruins",
                photographer=None,
                collection="ARCHNET",
                inventory_num="AN-67890",
                artist="Anonymous",
                orig_location="Damascus, Syria"
            ),
            ArchiveRecord(
                typ="Postcard",
                title="City Panorama",
                photographer="Richard P. McClary",
                collection="MIT Libraries",
                inventory_num="MIT-54321",
                orig_location="Cairo, Egypt"
            )
        ]


class TestUniqueIDGeneration(TestDataHandler):
    """Test unique ID generation functionality."""
    
    def test_generate_id_with_photographer(self, data_handler, sample_records):
        """Test ID generation when photographer is known."""
        record = sample_records[0]  # Patricia Blessing record
        unique_id = data_handler.generate_unique_id(record)
        
        assert unique_id == "PDB_LOC_LC-12345"
    
    def test_generate_id_without_photographer(self, data_handler, sample_records):
        """Test ID generation when photographer is unknown."""
        record = sample_records[1]  # No photographer
        unique_id = data_handler.generate_unique_id(record)
        
        assert unique_id == "HI_ARCHNET_AN-67890"
    
    def test_generate_id_with_unknown_photographer_mapping(self, data_handler):
        """Test ID generation with photographer not in mapping."""
        record = ArchiveRecord(
            typ="Modern Photo",
            photographer="John Doe",
            collection="Test Archive",
            inventory_num="TEST-123"
        )
        unique_id = data_handler.generate_unique_id(record)
        
        assert unique_id == "NN_TEST_TEST-123"
    
    def test_generate_id_with_missing_inventory_number(self, data_handler):
        """Test ID generation when inventory number is missing."""
        record = ArchiveRecord(
            typ="Modern Photo",
            photographer="Patricia Blessing",
            collection="Library of Congress"
        )
        unique_id = data_handler.generate_unique_id(record)
        
        assert unique_id == "PDB_LOC_UNKNOWN"
    
    def test_extract_collection_initial(self, data_handler):
        """Test extraction of collection initials."""
        test_cases = [
            ("Library of Congress", "LOC"),
            ("ARCHNET", "ARCHNET"),
            ("MIT Libraries", "MIT"),
            ("Harvard Art Museums", "HAM"),
            ("Metropolitan Museum of Art", "MET"),
            ("Victoria and Albert Museum", "VAM")
        ]
        
        for collection, expected in test_cases:
            result = data_handler._extract_collection_initial(collection)
            assert result == expected


class TestCSVOperations(TestDataHandler):
    """Test CSV file operations."""
    
    def test_save_to_csv_creates_file(self, data_handler, sample_records, temp_dir):
        """Test that save_to_csv creates a file."""
        filepath = Path(temp_dir) / "test_output.csv"
        data_handler.save_to_csv(sample_records, str(filepath))
        
        assert filepath.exists()
    
    def test_save_to_csv_correct_columns(self, data_handler, sample_records, temp_dir):
        """Test that CSV has correct column order."""
        filepath = Path(temp_dir) / "test_output.csv"
        data_handler.save_to_csv(sample_records, str(filepath))
        
        df = pd.read_csv(filepath)
        expected_columns = DataSchema().columns
        
        assert list(df.columns) == expected_columns
    
    def test_save_to_csv_includes_unique_ids(self, data_handler, sample_records, temp_dir):
        """Test that unique IDs are generated and included."""
        filepath = Path(temp_dir) / "test_output.csv"
        data_handler.save_to_csv(sample_records, str(filepath))
        
        df = pd.read_csv(filepath)
        
        assert df["Unique ID"].notna().all()
        assert df.loc[0, "Unique ID"] == "PDB_LOC_LC-12345"
        assert df.loc[1, "Unique ID"] == "HI_ARCHNET_AN-67890"
        assert df.loc[2, "Unique ID"] == "RPM_MIT_MIT-54321"
    
    def test_save_to_csv_preserves_data(self, data_handler, sample_records, temp_dir):
        """Test that all data is correctly preserved in CSV."""
        filepath = Path(temp_dir) / "test_output.csv"
        data_handler.save_to_csv(sample_records, str(filepath))
        
        df = pd.read_csv(filepath)
        
        # Check first record
        assert df.loc[0, "Title"] == "Mosque Interior View"
        assert df.loc[0, "Photographer"] == "Patricia Blessing"
        assert df.loc[0, "Collection"] == "Library of Congress"
        assert df.loc[0, "Typ"] == "Modern Photo"
    
    def test_save_empty_list(self, data_handler, temp_dir):
        """Test saving empty list creates CSV with headers only."""
        filepath = Path(temp_dir) / "empty.csv"
        data_handler.save_to_csv([], str(filepath))
        
        df = pd.read_csv(filepath)
        assert len(df) == 0
        assert list(df.columns) == DataSchema().columns


class TestSchemaValidation(TestDataHandler):
    """Test schema validation functionality."""
    
    def test_validate_schema_compliance_valid_data(self, data_handler, sample_records):
        """Test schema validation with valid data."""
        result = data_handler.validate_schema_compliance(sample_records)
        assert result is True
    
    def test_validate_schema_compliance_empty_list(self, data_handler):
        """Test schema validation with empty list."""
        result = data_handler.validate_schema_compliance([])
        assert result is True
    
    def test_record_to_dict_conversion(self, data_handler, sample_records):
        """Test conversion of ArchiveRecord to dictionary with correct column names."""
        record = sample_records[0]
        result = data_handler._record_to_dict(record)
        
        assert "Title" in result
        assert "Photographer" in result
        assert "Unique ID" in result
        assert result["Title"] == "Mosque Interior View"
        assert result["Photographer"] == "Patricia Blessing"