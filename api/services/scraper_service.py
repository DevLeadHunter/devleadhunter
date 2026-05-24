"""
Web scraper service for fetching prospect data.
"""
from typing import List, Optional
import asyncio
import logging
from models.prospect import ProspectCreate
from scrappers.base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class ScraperService:
    """
    Service for coordinating web scraping operations.
    
    This service manages multiple scrapers and orchestrates
    data collection from various sources.
    """
    
    def __init__(self):
        """Initialize the scraper service."""
        self._scrapers: List[BaseScraper] = []
        self._is_active = False
    
    async def add_scraper(self, scraper: BaseScraper) -> None:
        """
        Register a scraper with the service.
        
        Args:
            scraper: Scraper instance to register
        """
        if scraper not in self._scrapers:
            self._scrapers.append(scraper)
    
    async def remove_scraper(self, scraper: BaseScraper) -> None:
        """
        Unregister a scraper from the service.
        
        Args:
            scraper: Scraper instance to remove
        """
        if scraper in self._scrapers:
            self._scrapers.remove(scraper)
    
    async def scrape_all(
        self, 
        category: str, 
        city: str, 
        max_results: int = 50,
        source_filter: Optional[str] = None
    ) -> List[ProspectCreate]:
        """
        Run all registered scrapers and collect results.
        
        Args:
            category: Business category to search
            city: City to search in
            max_results: Maximum number of results per scraper
            source_filter: Optional source filter (e.g., 'google', 'mock', 'all')
            
        Returns:
            Combined list of prospects from all scrapers
            
        Example:
            >>> prospects = await scraper_service.scrape_all("restaurant", "Paris", 50, "google")
        """
        logger.info(f"[ScraperService] scrape_all called: category={category}, city={city}, max_results={max_results}, source_filter={source_filter}")
        
        if not self._scrapers:
            logger.warning("[ScraperService] No scrapers registered!")
            return []
        
        # Filter scrapers by source if needed
        scrapers_to_use = self._scrapers
        logger.info(f"Total scrapers registered: {len(self._scrapers)}")
        for s in self._scrapers:
            logger.info(f"Registered scraper: {s.__class__.__name__} with source: {s.source}")
        
        if source_filter and source_filter != "all":
            from enums.source import Source
            # Try to find matching source (case insensitive)
            source_filter_lower = source_filter.lower()
            target_source = None
            for source in Source:
                if source.value.lower() == source_filter_lower:
                    target_source = source
                    break
            
            if target_source is None:
                logger.warning(f"Unknown source filter: {source_filter}, using all scrapers")
            else:
                scrapers_to_use = [s for s in self._scrapers if s.source == target_source]
                logger.info(f"Filtering scrapers by source: {source_filter} -> {len(scrapers_to_use)} scrapers found")
                for s in scrapers_to_use:
                    logger.info(f"Selected scraper: {s.__class__.__name__} with source: {s.source}")
        else:
            logger.info(f"Using all scrapers: {len(scrapers_to_use)} scrapers available")
        
        # Run scrapers concurrently
        logger.info(f"Starting {len(scrapers_to_use)} scrapers...")
        for scraper in scrapers_to_use:
            logger.info(f"Calling scraper: {scraper.__class__.__name__} with category={category}, city={city}, max_results={max_results}")
        
        tasks = [
            scraper.scrape(category, city, max_results) 
            for scraper in scrapers_to_use
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results and filter exceptions
        all_prospects = []
        for i, result in enumerate(results):
            if isinstance(result, list):
                all_prospects.extend(result)
                logger.info(f"Scraper {i} returned {len(result)} prospects")
            elif isinstance(result, Exception):
                logger.error(f"Scraper {i} raised exception: {result}", exc_info=result)
        
        # Remove duplicates (simple name-based deduplication)
        seen = set()
        unique_prospects = []
        for prospect in all_prospects:
            key = (prospect.name.lower(), prospect.city.lower())
            if key not in seen:
                seen.add(key)
                unique_prospects.append(prospect)
        
        return unique_prospects[:max_results]
    
    async def get_status(self) -> dict:
        """
        Get status of all registered scrapers.
        
        Returns:
            Dictionary with scraper statuses
        """
        return {
            "total_scrapers": len(self._scrapers),
            "scraper_names": [s.__class__.__name__ for s in self._scrapers],
            "is_active": self._is_active
        }


# Global service instance
scraper_service = ScraperService()

