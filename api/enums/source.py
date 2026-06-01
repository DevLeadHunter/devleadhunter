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
        YELP: Yelp platform
        OSM: OpenStreetMap
        MOCK: Mock/test data
        ALL: All sources
    """
    
    GOOGLE = "google"
    PAGESJAUNES = "pagesjaunes"
    YELP = "yelp"
    OSM = "osm"
    MOCK = "mock"
    ALL = "all"
    AUTO = "auto"
    BRIGHTDATA = "brightdata"

