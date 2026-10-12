"""
Whether a prospected city has its place on the coverage map.
"""

from enum import Enum


class CityGeocodingStatus(str, Enum):
    """
    Where the lookup of a coverage-map city stands.

    Attributes:
        PLACED: The city's centre is known
        UNKNOWN: No geocoder knows the city (a typo, an abbreviation): it stays off the map
        PENDING: Not looked up yet, or the last lookup failed: the dashboard asks for it
    """

    PLACED = "placed"
    UNKNOWN = "unknown"
    PENDING = "pending"
