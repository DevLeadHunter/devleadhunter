"""
Base scraper class for web scraping operations.
"""
from abc import ABC, abstractmethod
from typing import List
from models.prospect import ProspectCreate
from enums.source import Source


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
        max_results: int = 50
    ) -> List[ProspectCreate]:
        """
        Scrape prospects from the source.
        
        Args:
            category: Business category to search for
            city: City to search in
            max_results: Maximum number of results to return
            
        Returns:
            List of ProspectCreate objects
            
        Raises:
            NotImplementedError: If not implemented by subclass
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

