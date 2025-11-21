"""
Scrapers package for Prospect Tool API.
"""

from .email_scraper import email_scraper
from .google_scraper import GoogleScraper
from .pagesjaunes_scraper import PagesJaunesScraper
from .yelp_scraper import YelpScraper
from .osm_scraper import OSMScraper
from .mappy_scraper import MappyScraper
from .mock_scraper import MockScraper

__all__ = [
    'email_scraper',
    'GoogleScraper',
    'PagesJaunesScraper',
    'YelpScraper',
    'OSMScraper',
    'MappyScraper',
    'MockScraper'
]

