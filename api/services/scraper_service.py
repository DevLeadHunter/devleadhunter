"""
Web scraper service for fetching prospect data.
"""
from __future__ import annotations

from typing import Callable, List, Optional
import logging

from models.prospect import ProspectCreate
from scrappers.base_scraper import BaseScraper
from services.scrape_progress import ScrapeProgressReporter

logger = logging.getLogger(__name__)


class ScraperService:
    """Service for coordinating web scraping operations."""

    def __init__(self) -> None:
        self._scrapers: List[BaseScraper] = []
        self._is_active = False

    async def add_scraper(self, scraper: BaseScraper) -> None:
        if scraper not in self._scrapers:
            self._scrapers.append(scraper)

    async def remove_scraper(self, scraper: BaseScraper) -> None:
        if scraper in self._scrapers:
            self._scrapers.remove(scraper)

    async def scrape_all(
        self,
        category: str,
        city: str,
        max_results: int = 50,
        source_filter: Optional[str] = None,
        *,
        only_without_website: bool = True,
        progress: Optional[ScrapeProgressReporter] = None,
        should_stop: Optional[Callable[[], bool]] = None,
    ) -> List[ProspectCreate]:
        """Run scrapers and collect results, optionally streaming progress."""
        logger.info(
            "[ScraperService] scrape_all category=%s city=%s max=%s source=%s",
            category,
            city,
            max_results,
            source_filter,
        )

        if not self._scrapers:
            if progress:
                await progress.log("Aucun scraper enregistré.")
            return []

        scrapers_to_use = self._scrapers
        if source_filter and source_filter != "all":
            from enums.source import Source

            target_source = next(
                (s for s in Source if s.value.lower() == source_filter.lower()),
                None,
            )
            if target_source is None:
                logger.warning("Unknown source filter: %s", source_filter)
            else:
                scrapers_to_use = [s for s in self._scrapers if s.source == target_source]

        all_prospects: list[ProspectCreate] = []
        seen: set[tuple[str, str]] = set()

        for scraper in scrapers_to_use:
            if should_stop and should_stop():
                break

            source_name = scraper.source.value
            if progress:
                await progress.log(f"Source {source_name} — lancement du scrape…")

            try:
                results = await scraper.scrape(
                    category,
                    city,
                    max_results,
                    only_without_website=only_without_website,
                    progress=progress,
                    should_stop=should_stop,
                )
            except Exception as exc:
                logger.error("Scraper %s failed: %s", scraper.__class__.__name__, exc, exc_info=True)
                if progress:
                    await progress.log(f"Source {source_name} — erreur : {exc}")
                continue

            if progress:
                await progress.log(f"Source {source_name} — {len(results)} résultat(s) brut(s)")

            for prospect in results:
                if should_stop and should_stop():
                    break
                key = (prospect.name.lower(), (prospect.city or "").lower())
                if key in seen:
                    continue
                seen.add(key)
                all_prospects.append(prospect)

            if len(all_prospects) >= max_results:
                break

        return all_prospects[:max_results]

    async def get_status(self) -> dict:
        return {
            "total_scrapers": len(self._scrapers),
            "scraper_names": [s.__class__.__name__ for s in self._scrapers],
            "is_active": self._is_active,
        }


scraper_service = ScraperService()
