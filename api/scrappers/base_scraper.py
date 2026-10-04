"""
Base scraper class for browser-driven scraping.
"""

from enums.source import Source


class BaseScraper:
    """Carries what every browser-driven scraper shares: its source and its running state."""

    def __init__(self, source: Source):
        """
        Initialize the scraper.

        Args:
            source: Source identifier for the scraper
        """
        self.source = source
        self._is_running = False

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
