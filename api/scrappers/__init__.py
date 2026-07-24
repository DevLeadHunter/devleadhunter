"""
Scrapers package for Prospect Tool API.
"""

from .email_scraper import email_scraper
from .google_scraper import GoogleScraper
from .osm_scraper import OSMScraper
from .pagesjaunes_scraper import PagesJaunesScraper

__all__ = [
    "GoogleScraper",
    "OSMScraper",
    "PagesJaunesScraper",
    "email_scraper",
]
