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
        MAPPY: Mappy platform
        MOCK: Mock/test data
        ALL: All sources
    """
    
    GOOGLE = "google"
    PAGESJAUNES = "pagesjaunes"
    YELP = "yelp"
    OSM = "osm"
    MAPPY = "mappy"
    MOCK = "mock"
    ALL = "all"

