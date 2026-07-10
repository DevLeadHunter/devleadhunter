"""
Source enum for prospect data sources.
"""
from enum import Enum


class Source(str, Enum):
    """
    Enum for data sources where prospects can be found.
    
    Attributes:
        GOOGLE: Google Business/Maps
        PAGESJAUNES: Pages Jaunes (French directory)
        YELP: Yelp platform (deprecated — scraper removed; kept for historical prospects)
        OSM: OpenStreetMap
        ALL: All sources
    """

    GOOGLE = "google"
    PAGESJAUNES = "pagesjaunes"
    # Deprecated: the Yelp scraper was removed. Kept so existing prospects with
    # source="yelp" still deserialize; not offered in the UI or scraper registry.
    YELP = "yelp"
    OSM = "osm"
    # Deprecated: the mock/test scraper was removed. Kept so existing prospects with
    # source="mock" still deserialize; not offered in the UI or scraper registry.
    MOCK = "mock"
    # Manually added or JSON-imported prospects (no scraper involved).
    MANUAL = "manual"
    ALL = "all"
    AUTO = "auto"
    BRIGHTDATA = "brightdata"

