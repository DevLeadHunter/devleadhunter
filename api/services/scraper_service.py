"""
Web scraper service for fetching prospect data.

Coordinates the sources with automatic FAILOVER: the requested source runs first and,
if it crashes / is blocked / returns nothing, the orchestrator cascades to the next
sources in :data:`_FAILOVER_ORDER` until it gets results. Every source run is classified
(ok / empty / blocked / timeout / error) and recorded for the admin monitoring page.
"""
from __future__ import annotations

import asyncio
from typing import Callable, List, Optional
import logging

from models.prospect import ProspectCreate
from scrappers import scrape_signals
from scrappers.base_scraper import BaseScraper
from services.scrape_progress import ScrapeProgressReporter
from services.scraper_diagnostics_service import (
    STATUS_BLOCKED,
    STATUS_EMPTY,
    STATUS_ERROR,
    STATUS_OK,
    STATUS_TIMEOUT,
    scraper_diagnostics_service,
)

logger = logging.getLogger(__name__)

# Failover priority — richest/most-specific first, paid unlocker before the sparse API.
# ``auto`` is intentionally excluded: it re-runs Pages Jaunes + OSM, which we already
# try individually, so including it would double-scrape those two.
_FAILOVER_ORDER: tuple[str, ...] = ("google", "pagesjaunes", "brightdata", "osm")


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

    def _ordered_candidates(self, source_filter: Optional[str]) -> tuple[List[BaseScraper], bool]:
        """Build the ordered list of scrapers to try, plus whether a source was requested.

        A specific request runs first, then the rest of the failover chain (so a blocked
        primary still cascades). ``all``/unset runs the whole failover chain.

        Returns:
            ``(candidates, is_specific)``.
        """
        by_source: dict[str, BaseScraper] = {}
        for scraper in self._scrapers:
            by_source.setdefault(scraper.source.value, scraper)

        is_specific = bool(source_filter and source_filter.lower() != "all")
        if is_specific:
            requested = source_filter.lower()  # type: ignore[union-attr]
            ordered_names = [requested] + [n for n in _FAILOVER_ORDER if n != requested]
        else:
            ordered_names = list(_FAILOVER_ORDER)

        candidates: List[BaseScraper] = []
        seen: set[str] = set()
        for name in ordered_names:
            scraper = by_source.get(name)
            if scraper is not None and name not in seen:
                candidates.append(scraper)
                seen.add(name)
        return candidates, is_specific

    async def _run_and_classify(
        self,
        scraper: BaseScraper,
        category: str,
        city: str,
        max_results: int,
        *,
        only_without_website: bool,
        progress: Optional[ScrapeProgressReporter],
        should_stop: Optional[Callable[[], bool]],
    ) -> tuple[List[ProspectCreate], str, Optional[str], Optional[str]]:
        """Run one scraper and classify the outcome.

        Returns:
            ``(results, status, error_message, html_snapshot)`` where status is one of ok / empty / blocked / timeout / error. A block is surfaced via :mod:`scrappers.scrape_signals` (captcha/anti-bot HTML captured by the scraper).
        """
        source = scraper.source.value
        scrape_signals.clear(source)
        status: str = STATUS_OK
        error_message: Optional[str] = None
        html_snapshot: Optional[str] = None
        results: List[ProspectCreate] = []

        try:
            results = await scraper.scrape(
                category,
                city,
                max_results,
                only_without_website=only_without_website,
                progress=progress,
                should_stop=should_stop,
            )
        except asyncio.TimeoutError as exc:
            status, error_message = STATUS_TIMEOUT, (str(exc) or "timeout")
            logger.warning("Scraper %s timed out", scraper.__class__.__name__)
        except Exception as exc:  # noqa: BLE001 — classify, don't abort the cascade
            status, error_message = STATUS_ERROR, str(exc)
            logger.error("Scraper %s failed: %s", scraper.__class__.__name__, exc, exc_info=True)

        block = scrape_signals.pop_block(source)
        if status == STATUS_OK:
            # Results present → OK, even if an earlier tier noted a block (the internal
            # cascade recovered — e.g. Pages Jaunes HTTP blocked but visible Chrome worked).
            if not results:
                if block is not None:
                    status, error_message, html_snapshot = STATUS_BLOCKED, block["reason"], block["html"]
                else:
                    status = STATUS_EMPTY
        elif block is not None:
            # An exception AND a captured block → prefer the block (more actionable).
            status, html_snapshot = STATUS_BLOCKED, block["html"]
            error_message = error_message or block["reason"]

        return results, status, error_message, html_snapshot

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
        user_id: Optional[int] = None,
    ) -> List[ProspectCreate]:
        """Run scrapers with automatic failover and stream/record progress."""
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

        candidates, is_specific = self._ordered_candidates(source_filter)
        if not candidates:
            # Unknown source or none matched the failover order — try everything registered.
            logger.warning("No candidate scraper for source=%s; using all registered", source_filter)
            candidates, is_specific = list(self._scrapers), False

        all_prospects: List[ProspectCreate] = []
        seen: set[tuple[str, str]] = set()

        for scraper in candidates:
            if should_stop and should_stop():
                break

            source_name = scraper.source.value
            if progress:
                await progress.log(f"Source {source_name} — lancement du scrape…")

            results, status, error_message, html_snapshot = await self._run_and_classify(
                scraper,
                category,
                city,
                max_results,
                only_without_website=only_without_website,
                progress=progress,
                should_stop=should_stop,
            )

            scraper_diagnostics_service.record(
                source=source_name,
                status=status,
                category=category,
                city=city,
                results_count=len(results),
                expected_count=max_results,
                error_message=error_message,
                html_snapshot=html_snapshot,
                user_id=user_id,
            )

            if progress:
                if status == STATUS_OK:
                    await progress.log(f"Source {source_name} — {len(results)} résultat(s) brut(s)")
                elif status == STATUS_BLOCKED:
                    await progress.log(f"Source {source_name} — bloquée (anti-bot), bascule vers la suivante…")
                elif status == STATUS_EMPTY:
                    await progress.log(f"Source {source_name} — 0 résultat, bascule vers la suivante…")
                else:
                    await progress.log(f"Source {source_name} — {status} : {error_message}")

            added = 0
            for prospect in results:
                if should_stop and should_stop():
                    break
                key = (prospect.name.lower(), (prospect.city or "").lower())
                if key in seen:
                    continue
                seen.add(key)
                all_prospects.append(prospect)
                added += 1

            if len(all_prospects) >= max_results:
                break
            # Failover: for a specific request, stop as soon as ANY source yields results
            # (the requested one if it worked, otherwise the first healthy fallback).
            if is_specific and added > 0:
                break

        return all_prospects[:max_results]

    async def get_status(self) -> dict:
        return {
            "total_scrapers": len(self._scrapers),
            "scraper_names": [s.__class__.__name__ for s in self._scrapers],
            "is_active": self._is_active,
        }


scraper_service = ScraperService()
