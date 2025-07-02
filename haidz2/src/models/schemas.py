"""Data schemas and models for the scraping agent."""

from typing import Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ArchiveRecord(BaseModel):
    """Schema for a single archive record."""
    
    unique_id: Optional[str] = Field(None, description="Generated unique identifier")
    typ: Optional[str] = Field(None, alias="Typ", description="Type of image (MP, HI, PC, etc.)")
    title: Optional[str] = Field(None, alias="Title")
    ce_start_date: Optional[str] = Field(None, alias="CE Start Date")
    ce_end_date: Optional[str] = Field(None, alias="CE End Date")
    ah_start_date: Optional[str] = Field(None, alias="AH Start Date")
    ah_end_date: Optional[str] = Field(None, alias="AH End Date")
    date_photograph_taken: Optional[str] = Field(None, alias="Date photograph taken")
    date_qualif: Optional[str] = Field(None, alias="Date Qualif.")
    medium: Optional[str] = Field(None, alias="Medium")
    technique: Optional[str] = Field(None, alias="Technique")
    measurements: Optional[str] = Field(None, alias="Measurements")
    artist: Optional[str] = Field(None, alias="Artist")
    orig_location: Optional[str] = Field(None, alias="Orig. Location")
    collection: Optional[str] = Field(None, alias="Collection")
    inventory_num: Optional[str] = Field(None, alias="Inventory #")
    folder: Optional[str] = Field(None, alias="Folder")
    photographer: Optional[str] = Field(None, alias="Photographer")
    copyright_for_photo: Optional[str] = Field(None, alias="Copyright for Photo")
    image_quality: Optional[str] = Field(None, alias="Image Quality")
    image_rights: Optional[str] = Field(None, alias="Image Rights")
    published_in: Optional[str] = Field(None, alias="Published in")
    notes: Optional[str] = Field(None, alias="Notes")

    model_config = ConfigDict(populate_by_name=True)
        

class DataSchema(BaseModel):
    """Defines the complete data schema for CSV output."""
    
    columns: List[str] = [
        "Unique ID",
        "Typ",
        "Title",
        "CE Start Date",
        "CE End Date",
        "AH Start Date",
        "AH End Date",
        "Date photograph taken",
        "Date Qualif.",
        "Medium",
        "Technique",
        "Measurements",
        "Artist",
        "Orig. Location",
        "Collection",
        "Inventory #",
        "Folder",
        "Photographer",
        "Copyright for Photo",
        "Image Quality",
        "Image Rights",
        "Published in",
        "Notes"
    ]
    
    def get_field_mapping(self) -> Dict[str, str]:
        """Returns mapping from model fields to CSV column names."""
        return {
            "unique_id": "Unique ID",
            "typ": "Typ",
            "title": "Title",
            "ce_start_date": "CE Start Date",
            "ce_end_date": "CE End Date",
            "ah_start_date": "AH Start Date",
            "ah_end_date": "AH End Date",
            "date_photograph_taken": "Date photograph taken",
            "date_qualif": "Date Qualif.",
            "medium": "Medium",
            "technique": "Technique",
            "measurements": "Measurements",
            "artist": "Artist",
            "orig_location": "Orig. Location",
            "collection": "Collection",
            "inventory_num": "Inventory #",
            "folder": "Folder",
            "photographer": "Photographer",
            "copyright_for_photo": "Copyright for Photo",
            "image_quality": "Image Quality",
            "image_rights": "Image Rights",
            "published_in": "Published in",
            "notes": "Notes"
        }


class UniqueIDMappings(BaseModel):
    """Mappings for unique ID generation."""
    
    photographer_initials: Dict[str, str] = {
        "Patricia Blessing": "PDB",
        "Richard P. McClary": "RPM",
        "Fatih Han": "FH",
        "Belgin Turan Özkaya": "BTO",
        "Menna M. ElMahy": "MME",
        "Michelle Lynch Köycü": "MLK",
        "No Name": "NN",
        "Unknown": "NN"
    }
    
    type_initials: Dict[str, str] = {
        "Modern Photo": "MP",
        "MP": "MP",  # Also accept abbreviation
        "Historical Image": "HI",
        "HI": "HI",
        "Postcard": "PC",
        "PC": "PC",
        "Screenshot": "SS",
        "SS": "SS",
        "Scan": "SC",
        "SC": "SC",
        "Painting": "PT",
        "PT": "PT",
        "Illustration": "IT",
        "IT": "IT"
    }