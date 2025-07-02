"""
Archive-specific patterns and strategies for known archive sites.
These patterns help the autonomous agent better understand common archive structures.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ArchivePattern(BaseModel):
    """Pattern definition for a specific archive type."""
    
    name: str
    domain: str
    wait_strategy: str = Field(default="networkidle", description="domcontentloaded, networkidle, or custom")
    wait_selectors: List[str] = Field(default_factory=list, description="Selectors to wait for")
    container_hints: List[str] = Field(default_factory=list, description="Common container selectors")
    item_hints: List[str] = Field(default_factory=list, description="Common item selectors")
    navigation_hints: Dict[str, List[str]] = Field(default_factory=dict, description="Navigation patterns")
    metadata_mappings: Dict[str, List[str]] = Field(default_factory=dict, description="Field name mappings")
    javascript_required: bool = Field(default=False)
    export_available: bool = Field(default=False)
    export_selector: Optional[str] = None
    pre_navigation_required: bool = Field(default=False, description="Requires navigation before data appears")
    pre_navigation_steps: List[Dict[str, Any]] = Field(default_factory=list, description="Steps to perform before data appears")
    

KNOWN_PATTERNS = {
    "archnet.org": ArchivePattern(
        name="ArchNet",
        domain="archnet.org",
        wait_strategy="domcontentloaded",
        wait_selectors=[".site-grid", ".collection-grid", "[class*='grid']"],
        container_hints=[
            ".site-grid", ".collection-grid", ".search-results",
            "[class*='grid']", "[class*='results']", ".content",
            ".sites-list", "main", "[role='main']"
        ],
        item_hints=[
            ".site-item", ".collection-item", ".search-result",
            "[class*='card']", "[class*='item']", "article",
            ".grid-item", "[class*='site-card']", "[class*='result']"
        ],
        navigation_hints={
            "pagination": ["a[href*='page=']", ".pagination a", ".pager a", "[class*='pagination']"],
            "next": ["a:contains('Next')", ".next", "a[rel='next']", "[aria-label='Next']"],
            "collections": ["a[href*='/collections/']", ".collection-link"],
            "sites": ["a[href*='/sites/']", ".site-link"]
        },
        metadata_mappings={
            "title": ["h2", "h3", ".title", ".name", "[class*='title']", "a"],
            "type": ["Type:", "Category:", ".type"],
            "location": ["Location:", "Site:", ".location", "[class*='location']"],
            "date": ["Date:", "Period:", ".date"],
            "collection": ["Collection:", ".collection-name", "ArchNet"]
        },
        javascript_required=True,
        pre_navigation_required=True,
        pre_navigation_steps=[
            {
                "action": "navigate_to_data",
                "target_url": "/sites",
                "wait_after": 5000
            }
        ]
    ),
    
    "manar-al-athar.ox.ac.uk": ArchivePattern(
        name="Manar al-Athar",
        domain="manar-al-athar.ox.ac.uk",
        wait_strategy="domcontentloaded",
        wait_selectors=[".thumbnails", "#results", ".search-results"],
        container_hints=[
            ".thumbnails", "#results", ".search-results",
            "[class*='result']", "[class*='thumbnail']"
        ],
        item_hints=[
            ".thumbnail", ".result-item", "li.item",
            "[class*='photo']", "[class*='image']"
        ],
        navigation_hints={
            "pagination": ["a[href*='page=']", ".pagination a"],
            "results_per_page": ["select[name*='per_page']", "#results_per_page"],
            "export": ["a:contains('CSV')", "a[href*='export']", ".export-link"]
        },
        metadata_mappings={
            "title": [".caption", ".title", "img[alt]"],
            "location": [".location", ".site-name"],
            "filename": [".filename", ".image-name"],
            "date": [".date", ".year"]
        },
        javascript_required=False,
        export_available=True,
        export_selector="a[href*='export=csv']"
    ),
    
    "saltresearch.org": ArchivePattern(
        name="SALT Research",
        domain="saltresearch.org",
        wait_strategy="custom",
        wait_selectors=["prm-search-result", "[class*='result']", "#searchResults"],
        container_hints=[
            "prm-search-results-list", "#searchResults", ".results-container",
            "[class*='search-result']", "prm-brief-result-container"
        ],
        item_hints=[
            "prm-brief-result", ".result-item", "[class*='brief-result']",
            "prm-search-result"
        ],
        navigation_hints={
            "pagination": ["prm-paginator", ".pagination"],
            "next": ["button[aria-label*='Next']", ".next-page"]
        },
        metadata_mappings={
            "title": ["h3", ".item-title", "prm-brief-result-container h3"],
            "type": [".resource-type", ".format"],
            "date": [".creation-date", ".date"],
            "creator": [".creator", ".author"]
        },
        javascript_required=True
    ),
    
    "nit-istanbul.org": ArchivePattern(
        name="Machiel Kiel Archive",
        domain="nit-istanbul.org",
        wait_strategy="domcontentloaded",
        container_hints=[
            ".gallery", "#gallery", "[class*='photo']",
            ".content", "table", "td",
            "div.picture", ".picture"
        ],
        item_hints=[
            "div.picture", ".picture",
            "div:has(> a[href*='.jpg'])", "div:has(> a[href*='.JPG'])",
            "a[href*='.jpg']", "a[href*='.JPG']"
        ],
        navigation_hints={
            "pagination": ["a[href*='page']", ".page-link"],
            "galleries": ["a[href*='gallery']", "a[href*='album']"]
        },
        metadata_mappings={
            "title": ["img[alt]", ".caption", "td", "a"],
            "location": [".location", "td"],
            "filename": ["img[src]", "a[href*='.jpg']"]
        },
        javascript_required=False,
        pre_navigation_required=True,
        pre_navigation_steps=[
            {
                "action": "select",
                "selector": "select:first-of-type",
                "value": "Turkey",
                "wait_after": 1000
            },
            {
                "action": "select", 
                "selector": "select:nth-of-type(2)",
                "value": "Edirne",
                "wait_after": 2000
            }
        ]
    ),
    
    "akkasah.org": ArchivePattern(
        name="Akkasah Center",
        domain="akkasah.org",
        wait_strategy="networkidle",
        container_hints=[
            ".collection-grid", ".photo-grid", "[class*='collection']",
            ".results", "#photos"
        ],
        item_hints=[
            ".photo-item", ".collection-item", "[class*='photo']",
            "article", ".result"
        ],
        navigation_hints={
            "pagination": [".pagination", "a[href*='page']"],
            "collections": ["a[href*='/collection']", ".collection-link"]
        },
        metadata_mappings={
            "title": [".title", "h3", ".photo-title"],
            "photographer": [".photographer", ".creator"],
            "date": [".date", ".year"],
            "collection": [".collection-name"]
        },
        javascript_required=True
    )
}


def get_pattern_for_url(url: str) -> Optional[ArchivePattern]:
    """Get the archive pattern for a given URL."""
    for domain, pattern in KNOWN_PATTERNS.items():
        if domain in url:
            return pattern
    return None


def get_wait_strategy(url: str) -> Dict[str, Any]:
    """Get the appropriate wait strategy for a URL."""
    pattern = get_pattern_for_url(url)
    
    if not pattern:
        # Default strategy
        return {
            "wait_until": "networkidle",
            "timeout": 60000,
            "wait_selectors": []
        }
    
    strategy = {
        "wait_until": pattern.wait_strategy if pattern.wait_strategy != "custom" else "domcontentloaded",
        "timeout": 90000 if pattern.javascript_required else 60000,
        "wait_selectors": pattern.wait_selectors
    }
    
    return strategy