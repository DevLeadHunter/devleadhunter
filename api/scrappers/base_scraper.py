"""
Base scraper class for web scraping operations.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Optional

from enums.source import Source
from models.prospect import ProspectCreate

if TYPE_CHECKING:
    from services.scrape_progress import ScrapeProgressReporter


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.

    This class defines the interface that all scrapers must implement.
    Concrete scrapers should inherit from this class and implement
    the required methods.
    """

    def __init__(self, source: Source):
        """
        Initialize the scraper.

        Args:
            source: Source identifier for the scraper
        """
        self.source = source
        self._is_running = False

    @abstractmethod
    async def scrape(
        self,
        category: str,
        city: str,
        max_results: int = 50,
        *,
        only_without_website: bool = True,
        progress: Optional["ScrapeProgressReporter"] = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> list[ProspectCreate]:
        """
        Scrape prospects from the source.

        Args:
            category: Business category to search for
            city: City to search in
            max_results: Maximum number of results to return
            only_without_website: When True, skip prospects that already have a website

        Returns:
            List of ProspectCreate objects
        """
        raise NotImplementedError("Subclasses must implement scrape method")

    @property
    def is_running(self) -> bool:
        """
        Check if the scraper is currently running.

        Returns:
            True if scraper is running, False otherwise
        """
        return self._is_running

    async def start(self) -> None:
        """Start the scraper."""
        self._is_running = True

    async def stop(self) -> None:
        """Stop the scraper."""
        self._is_running = False

    def __repr__(self) -> str:
        """String representation of the scraper."""
        return f"{self.__class__.__name__}(source='{self.source}')"
