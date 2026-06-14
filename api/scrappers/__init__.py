"""
Scrapers package for Prospect Tool API.
"""

from .email_scraper import email_scraper
from .google_scraper import GoogleScraper
from .pagesjaunes_scraper import PagesJaunesScraper
from .osm_scraper import OSMScraper
from .mock_scraper import MockScraper

__all__ = [
    'email_scraper',
    'GoogleScraper',
    'PagesJaunesScraper',
    'OSMScraper',
    'MockScraper'
]

