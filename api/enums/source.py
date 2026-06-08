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
        MOCK: Mock/test data
        ALL: All sources
    """

    GOOGLE = "google"
    PAGESJAUNES = "pagesjaunes"
    # Deprecated: the Yelp scraper was removed. Kept so existing prospects with
    # source="yelp" still deserialize; not offered in the UI or scraper registry.
    YELP = "yelp"
    OSM = "osm"
    MOCK = "mock"
    ALL = "all"
    AUTO = "auto"
    BRIGHTDATA = "brightdata"

