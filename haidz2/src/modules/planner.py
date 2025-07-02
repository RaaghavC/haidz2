"""Planner module for generating scraping strategies from analysis results."""

from typing import List, Dict, Optional, Tuple
import re
from difflib import SequenceMatcher

from src.models.schemas import DataSchema
from src.models.strategies import (
    AnalysisResult, DataContainer, NavigationPattern,
    ScrapingStrategy, FieldMapping, NavigationStrategy
)


class Planner:
    """Generates executable scraping strategies based on page analysis."""
    
    def __init__(self):
        """Initialize the Planner."""
        self.semantic_mappings = {
            # Schema field -> possible web field names
            "Title": ["title", "name", "heading", "headline", "subject"],
            "Artist": ["artist", "creator", "author", "maker", "by"],
            "Photographer": ["photographer", "photo by", "photography", "shot by", "creator"],
            "Date photograph taken": ["date", "taken", "captured", "photographed", "shot date"],
            "Collection": ["collection", "archive", "repository", "source", "library"],
            "Inventory #": ["inventory", "accession", "id", "number", "catalog", "reference"],
            "Medium": ["medium", "material", "type", "format"],
            "Technique": ["technique", "process", "method"],
            "Measurements": ["measurements", "dimensions", "size", "scale"],
            "Orig. Location": ["location", "place", "site", "where", "origin"],
            "Notes": ["notes", "description", "comments", "remarks", "info"]
        }
    
    def generate_strategy(self, analysis: AnalysisResult, schema: DataSchema) -> ScrapingStrategy:
        """
        Generate a complete scraping strategy from analysis results.
        
        Args:
            analysis: Results from page analysis
            schema: Target data schema
            
        Returns:
            ScrapingStrategy ready for execution
        """
        # Map fields to selectors
        field_mapping = self.map_fields_to_selectors(
            analysis.data_containers, schema
        )
        
        # Determine navigation approach
        navigation_strategy = self.determine_navigation_approach(
            analysis.navigation_pattern
        )
        
        # Get container info from best container
        container_selector = None
        item_selector = None
        
        if analysis.data_containers:
            best_container = sorted(analysis.data_containers, 
                                    key=lambda c: c.confidence, reverse=True)[0]
            container_selector = best_container.selector
            item_selector = best_container.item_selector
        
        # Build complete strategy
        strategy = ScrapingStrategy(
            url=analysis.url,
            field_mapping=field_mapping,
            navigation_strategy=navigation_strategy,
            container_selector=container_selector,
            item_selector=item_selector,
            extraction_method="css_selector",
            wait_conditions=self._determine_wait_conditions(analysis),
            error_handling=self._define_error_handling()
        )
        
        return strategy
    
    def map_fields_to_selectors(self, containers: List[DataContainer], 
                                 schema: DataSchema) -> FieldMapping:
        """
        Map schema fields to CSS selectors from containers.
        
        Args:
            containers: Detected data containers
            schema: Target data schema
            
        Returns:
            FieldMapping with mapped and unmapped fields
        """
        mappings = {}
        confidence_scores = {}
        
        # Prioritize containers by confidence
        sorted_containers = self._prioritize_containers(containers)
        
        if not sorted_containers:
            # No containers found
            return FieldMapping(
                mappings={},
                confidence_scores={},
                unmapped_fields=schema.columns
            )
        
        # Use the best container
        best_container = sorted_containers[0]
        
        # Check if this is a label-value structure
        if best_container.field_selectors.get("_structure_type") == "label-value":
            # For label-value structures, we need to match based on the actual field names from sample data
            if best_container.sample_data:
                sample = best_container.sample_data[0]
                for schema_field in schema.columns:
                    if schema_field == "Unique ID":
                        continue
                    
                    best_match = None
                    best_score = 0.0
                    
                    # Try to match with sample data fields
                    for web_field in sample.keys():
                        score = self._match_field_semantically(web_field, schema_field)
                        
                        if score > best_score:
                            best_score = score
                            best_match = web_field
                    
                    # For label-value structure, we use a special selector format
                    if best_match and best_score > 0.5:
                        # This will be handled specially by the executor
                        mappings[schema_field] = f"_label_value:{best_match}"
                        confidence_scores[schema_field] = best_score
        else:
            # Map each schema field using regular selectors
            for schema_field in schema.columns:
                if schema_field == "Unique ID":
                    # Skip - generated later
                    continue
                
                best_match = None
                best_score = 0.0
                
                # Try to find matching selector
                for field_name, selector in best_container.field_selectors.items():
                    score = self._match_field_semantically(field_name, schema_field)
                    
                    if score > best_score:
                        best_score = score
                        best_match = (field_name, selector)
            
                # Accept matches above threshold
                if best_match and best_score > 0.5:
                    mappings[schema_field] = best_match[1]
                    confidence_scores[schema_field] = best_score
        
        # Determine unmapped fields
        unmapped_fields = [
            field for field in schema.columns 
            if field not in mappings and field != "Unique ID"
        ]
        
        return FieldMapping(
            mappings=mappings,
            confidence_scores=confidence_scores,
            unmapped_fields=unmapped_fields
        )
    
    def determine_navigation_approach(self, 
                                      nav_pattern: Optional[NavigationPattern]) -> NavigationStrategy:
        """
        Determine the navigation strategy based on detected patterns.
        
        Args:
            nav_pattern: Detected navigation pattern
            
        Returns:
            NavigationStrategy for page traversal
        """
        if not nav_pattern:
            return NavigationStrategy(
                method="none",
                selectors={},
                parameters={}
            )
        
        if nav_pattern.type == "pagination":
            return NavigationStrategy(
                method="click_next",
                selectors={
                    "next": nav_pattern.next_selector or "",
                    "pagination": nav_pattern.pagination_selector or ""
                },
                parameters={
                    "max_pages": nav_pattern.total_pages or 100,
                    "wait_after_click": 2000  # milliseconds
                }
            )
        
        elif nav_pattern.type == "infinite_scroll":
            return NavigationStrategy(
                method="scroll",
                selectors={},
                parameters={
                    "scroll_pause_time": 2000,  # milliseconds
                    "max_scrolls": 50,
                    "check_element": ".load-more"
                }
            )
        
        elif nav_pattern.type == "next_prev":
            return NavigationStrategy(
                method="click_next",
                selectors={
                    "next": nav_pattern.next_selector or ""
                },
                parameters={
                    "max_pages": 100,
                    "wait_after_click": 2000
                }
            )
        
        else:
            return NavigationStrategy(
                method="none",
                selectors={},
                parameters={}
            )
    
    def _match_field_semantically(self, web_field: str, schema_field: str) -> float:
        """
        Calculate semantic similarity between field names.
        
        Args:
            web_field: Field name from web page
            schema_field: Field name from schema
            
        Returns:
            Similarity score between 0 and 1
        """
        # Normalize strings
        web_field = web_field.lower().strip().replace('_', ' ').replace('#', '')
        schema_field = schema_field.lower().strip().replace('.', '')
        
        # Exact match
        if web_field == schema_field:
            return 1.0
        
        # Special cases for common variations (check these BEFORE substring matching)
        exact_mappings = {
            ("inventory #", "inventory #"): 1.0,
            ("orig location", "orig location"): 1.0,
            ("date photograph taken", "date photograph taken"): 1.0,
            ("typ", "typ"): 1.0,
            ("type", "typ"): 1.0,
            ("title", "title"): 1.0,
            ("artist", "artist"): 1.0,
            ("collection", "collection"): 1.0,
            ("medium", "medium"): 1.0,
            ("photographer", "photographer"): 1.0,
            ("location", "orig location"): 0.9,
            ("archive id", "inventory #"): 0.9,
            ("date taken", "date photograph taken"): 0.9,
            ("artist/architect", "artist"): 0.8,
        }
        
        for (web_norm, schema_norm), score in exact_mappings.items():
            if web_field == web_norm and schema_field == schema_norm:
                return score
        
        # Prevent incorrect date mappings
        if "date photograph taken" in web_field:
            # Only match to the exact "date photograph taken" field
            if schema_field != "date photograph taken":
                return 0.0
        
        # Prevent mapping date fields to non-date fields
        if "date" in web_field and "date" not in schema_field:
            return 0.0
            
        # Check if one contains the other (but be more selective)
        if len(web_field) > 3 and len(schema_field) > 3:  # Avoid short substring matches
            if web_field in schema_field or schema_field in web_field:
                # But reduce score if it's a partial match
                return 0.6
        
        # Check semantic mappings
        if schema_field.title() in self.semantic_mappings:
            keywords = self.semantic_mappings[schema_field.title()]
            for keyword in keywords:
                if keyword == web_field:  # Exact match only
                    return 0.7
        
        # Calculate string similarity
        similarity = SequenceMatcher(None, web_field, schema_field).ratio()
        
        # Only boost if BOTH contain the same key term
        key_terms = ["artist", "collection", "inventory", "technique", "measurements"]
        for term in key_terms:
            if term in web_field and term in schema_field:
                similarity = min(similarity + 0.2, 1.0)
        
        return similarity
    
    def _prioritize_containers(self, containers: List[DataContainer]) -> List[DataContainer]:
        """Sort containers by confidence and field count."""
        return sorted(
            containers,
            key=lambda c: (c.confidence, len(c.field_selectors)),
            reverse=True
        )
    
    def _calculate_mapping_confidence(self, mapping: FieldMapping, 
                                      total_fields: int) -> float:
        """Calculate overall confidence for a field mapping."""
        if total_fields == 0:
            return 0.0
        
        mapped_ratio = len(mapping.mappings) / total_fields
        
        # Average confidence of mapped fields
        if mapping.confidence_scores:
            avg_confidence = sum(mapping.confidence_scores.values()) / len(mapping.confidence_scores)
        else:
            avg_confidence = 0.0
        
        # Weighted score
        return (mapped_ratio * 0.6) + (avg_confidence * 0.4)
    
    def _determine_wait_conditions(self, analysis: AnalysisResult) -> List[str]:
        """Determine what elements to wait for before scraping."""
        conditions = []
        
        # Wait for main container
        if analysis.data_containers:
            conditions.append(f"selector:{analysis.data_containers[0].selector}")
        
        # Wait for navigation if present
        if analysis.navigation_pattern and analysis.navigation_pattern.pagination_selector:
            conditions.append(f"selector:{analysis.navigation_pattern.pagination_selector}")
        
        # Default wait
        if not conditions:
            conditions.append("domcontentloaded")
        
        return conditions
    
    def _define_error_handling(self) -> Dict[str, str]:
        """Define error handling strategies."""
        return {
            "timeout": "retry_with_longer_wait",
            "selector_not_found": "mark_field_as_missing",
            "navigation_failed": "save_current_data",
            "rate_limit": "exponential_backoff"
        }