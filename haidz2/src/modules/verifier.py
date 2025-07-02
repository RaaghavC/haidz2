"""Verifier module for data validation and quality checks."""

import re
from typing import List, Dict, Any, Set
from datetime import datetime

from src.models.schemas import DataSchema
from src.models.strategies import VerificationResult


class Verifier:
    """Validates scraped data quality and completeness."""
    
    def __init__(self):
        """Initialize the Verifier."""
        self.critical_fields = self._get_critical_fields()
        self.quality_patterns = {
            "placeholder": re.compile(r'^(\.\.\.|N/A|n/a|Unknown|unknown|TBD|tbd|-+)$'),
            "truncated": re.compile(r'\.\.\.$'),
            "date": re.compile(r'^\d{4}(-\d{2}(-\d{2})?)?$'),
            "whitespace": re.compile(r'^\s*$')
        }
    
    def verify_data(self, data: List[Dict[str, Any]], schema: DataSchema) -> VerificationResult:
        """
        Verify scraped data quality and completeness.
        
        Args:
            data: List of scraped records
            schema: Expected data schema
            
        Returns:
            VerificationResult with validation details
        """
        if not data:
            return VerificationResult(
                is_valid=False,
                completeness_score=0.0,
                quality_score=0.0,
                missing_fields=[],
                invalid_records=[],
                error_messages=["No data to verify"],
                recommendations=["No data was extracted. Check if the scraping strategy is correct."]
            )
        
        # Track issues
        all_missing_fields = set()
        invalid_records = []
        error_messages = []
        
        # Validate each record
        valid_records = []
        for idx, record in enumerate(data):
            if not isinstance(record, dict):
                invalid_records.append(idx)
                error_messages.append(f"Record {idx} is not a dictionary")
                continue
            
            # Check required fields
            missing = self.check_required_fields(record, schema)
            if missing:
                all_missing_fields.update(missing)
                if any(field in self.critical_fields for field in missing):
                    invalid_records.append(idx)
            else:
                valid_records.append(record)
            
            # Validate data types
            type_issues = self.validate_data_types(record, schema)
            if type_issues:
                error_messages.extend(type_issues)
        
        # Calculate scores
        completeness_score = self._calculate_completeness_score(data, schema)
        quality_score = self.assess_extraction_quality(valid_records)
        
        # Count only dict records for validity calculation
        dict_records = [r for r in data if isinstance(r, dict)]
        valid_record_ratio = len(valid_records) / len(dict_records) if dict_records else 0
        
        # Determine overall validity
        is_valid = (
            valid_record_ratio > 0.8 and  # More than 80% valid records
            completeness_score > 0.6 and
            quality_score > 0.5
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            all_missing_fields, completeness_score, quality_score
        )
        
        return VerificationResult(
            is_valid=is_valid,
            completeness_score=completeness_score,
            quality_score=quality_score,
            missing_fields=list(all_missing_fields),
            invalid_records=invalid_records,
            error_messages=error_messages,
            recommendations=recommendations
        )
    
    def check_required_fields(self, record: Dict[str, Any], schema: DataSchema) -> List[str]:
        """
        Check for missing required fields in a record.
        
        Args:
            record: Data record to check
            schema: Expected schema
            
        Returns:
            List of missing field names
        """
        missing = []
        
        for field in self.critical_fields:
            if field not in record or record.get(field) is None or str(record.get(field, "")).strip() == "":
                missing.append(field)
        
        return missing
    
    def validate_data_types(self, record: Dict[str, Any], schema: DataSchema) -> List[str]:
        """
        Validate data types in a record.
        
        Args:
            record: Data record to validate
            schema: Expected schema
            
        Returns:
            List of validation issues
        """
        issues = []
        
        for field, value in record.items():
            if value is None:
                continue
            
            # Check date fields
            if "date" in field.lower() and value:
                if not self._is_valid_date(str(value)):
                    issues.append(f"{field} has invalid date format: {value}")
            
            # Check numeric fields should be strings
            if field == "Inventory #" and isinstance(value, (int, float)):
                issues.append(f"{field} should be a string, not a number")
        
        return issues
    
    def assess_extraction_quality(self, data: List[Dict[str, Any]]) -> float:
        """
        Assess the quality of extracted data.
        
        Args:
            data: List of data records
            
        Returns:
            Quality score between 0 and 1
        """
        if not data:
            return 0.0
        
        total_score = 0
        field_count = 0
        
        for record in data:
            for field, value in record.items():
                if value is not None:
                    field_score = self._calculate_field_quality(field, str(value))
                    total_score += field_score
                    field_count += 1
        
        return total_score / field_count if field_count > 0 else 0.0
    
    def _get_critical_fields(self) -> Set[str]:
        """Get the set of critical required fields."""
        return {
            "Title",
            "Collection", 
            "Inventory #"
        }
    
    def _calculate_completeness_score(self, data: List[Dict[str, Any]], 
                                      schema: DataSchema) -> float:
        """Calculate how complete the data is relative to schema."""
        if not data:
            return 0.0
        
        expected_fields = set(schema.columns) - {"Unique ID"}  # Exclude generated field
        
        total_possible = len(expected_fields) * len(data)
        total_present = 0
        
        for record in data:
            if not isinstance(record, dict):
                continue
            for field in expected_fields:
                if field in record and record[field] is not None:
                    # Check if it's not just a placeholder
                    value = str(record[field]).strip()
                    if value and not self.quality_patterns["placeholder"].match(value):
                        total_present += 1
        
        return total_present / total_possible if total_possible > 0 else 0.0
    
    def _calculate_field_quality(self, field_name: str, value: str) -> float:
        """Calculate quality score for a single field value."""
        if not value or not value.strip():
            return 0.0
        
        value = value.strip()
        
        # Check for placeholder values
        if self.quality_patterns["placeholder"].match(value):
            return 0.2
        
        # Check for truncated values
        if self.quality_patterns["truncated"].match(value):
            return 0.5
        
        # Check for very short values
        if len(value) < 3:
            return 0.4
        
        # Special handling for certain fields
        if field_name == "Title" and len(value) < 5:
            return 0.5
        
        if "Date" in field_name and value:
            return 0.9 if self._is_valid_date(value) else 0.3
        
        # Good quality value
        return 0.9
    
    def _is_valid_date(self, value: str) -> bool:
        """Check if a value is a valid date."""
        # Check common date patterns
        if self.quality_patterns["date"].match(value):
            return True
        
        # Try parsing as date
        date_formats = [
            "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y",
            "%Y", "%B %d, %Y", "%d %B %Y"
        ]
        
        for fmt in date_formats:
            try:
                datetime.strptime(value, fmt)
                return True
            except ValueError:
                continue
        
        return False
    
    def _generate_recommendations(self, missing_fields: Set[str], 
                                  completeness_score: float,
                                  quality_score: float) -> List[str]:
        """Generate recommendations for improving data quality."""
        recommendations = []
        
        # Check for missing critical fields
        missing_critical = missing_fields & self.critical_fields
        if missing_critical:
            recommendations.append(
                f"Critical fields missing: {', '.join(missing_critical)}. "
                "Adjust selectors to capture these required fields."
            )
        
        # Check completeness
        if completeness_score < 0.6:
            recommendations.append(
                f"Low field coverage ({completeness_score:.1%}). "
                "Consider improving field mapping to extract additional metadata."
            )
        
        # Check quality
        if quality_score < 0.6:
            recommendations.append(
                f"Low data quality score ({quality_score:.1%}). "
                "Many fields contain placeholder values or are poorly extracted."
            )
        
        # Suggest strategy adjustments
        if len(recommendations) > 1:
            recommendations.append(
                "Consider re-analyzing the page structure and adjusting the scraping strategy."
            )
        
        return recommendations