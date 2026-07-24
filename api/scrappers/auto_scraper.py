"""
Auto scraper: combines OSM + Pages Jaunes in parallel then enriches emails.

Strategy
--------
1. Launch OSM (pure HTTP, fast) and Pages Jaunes (Chrome, rich data) at the same time
   via ``asyncio.gather()``.  OSM runs directly on the uvicorn event loop; Pages Jaunes
   dispatches to the dedicated nodriver thread loop — both are genuinely concurrent.
2. Merge results and deduplicate by normalised business name.
3. Enrich emails sequentially using the smart strategy:
   ``"{name}" "{phone}"``  →  ``"{name}" "{city}" email``  →  broad fallback.
   Phone-based queries (validated with BrightData) hit guide-artisan.fr, annuaires RGE,
   initiative-broceliande.bzh in the first result page.
"""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from collections.abc import Callable

from enums.source import Source
from models.prospect import ProspectCreate
from services.scrape_progress import ScrapeProgressReporter
from services.validation_service import validation_service

from .base_scraper import BaseScraper
from .email_scraper import email_scraper
from .osm_scraper import OSMScraper
from .pagesjaunes_scraper import PagesJaunesScraper

logger = logging.getLogger(__name__)


class AutoScraper(BaseScraper):
    """
    Intelligent auto scraper: OSM + Pages Jaunes in parallel + smart email enrichment.

    Registered as source ``auto``.  Each individual prospect keeps its original source
    label (``osm`` or ``pagesjaunes``) so you can see where it came from.
    """

    def __init__(self) -> None:
        super().__init__(source=Source.AUTO)
        # Fresh instances — independent from the scrapers registered in scraper_service
        self._osm = OSMScraper()
        self._pj = PagesJaunesScraper()

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Return a canonical key for deduplication (accent-free, lowercase, no punct)."""
        # Strip accents
        nfd = unicodedata.normalize("NFD", name)
        name = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
        # Lowercase, collapse non-word characters to spaces
        name = name.lower()
        name = re.sub(r"[^\w\s]", " ", name)
        name = re.sub(r"\s+", " ", name).strip()
        return name

    async def _run_osm(
        self,
        category: str,
        city: str,
        max_results: int,
        only_without_website: bool,
        progress: ScrapeProgressReporter | None,
        should_stop: Callable[[], bool] | None,
    ) -> list[ProspectCreate]:
        """Run OSMScraper, swallowing any exception so gather() always gets a list."""
        try:
            return await self._osm.scrape(
                category,
                city,
                max_results,
                only_without_website=only_without_website,
                progress=None,  # progress reported by AutoScraper directly
                should_stop=should_stop,
            )
        except Exception as exc:
            logger.error("[Auto] OSM scraper failed: %s", exc)
            return []

    async def _run_pj(
        self,
        category: str,
        city: str,
        max_results: int,
        only_without_website: bool,
        progress: ScrapeProgressReporter | None,
        should_stop: Callable[[], bool] | None,
    ) -> list[ProspectCreate]:
        """Run PagesJaunesScraper, swallowing any exception."""
        try:
            return await self._pj.scrape(
                category,
                city,
                max_results,
                only_without_website=only_without_website,
                progress=None,
                should_stop=should_stop,
            )
        except Exception as exc:
            logger.error("[Auto] PagesJaunes scraper failed: %s", exc)
            return []

    async def _enrich_email(self, prospect: ProspectCreate) -> ProspectCreate:
        """
        Try to find a missing email via smart Google search.

        Uses the phone number when available (most accurate strategy).
        Skips if the prospect already has an email.
        """
        if prospect.email:
            return prospect
        try:
            found = await email_scraper.find_email_smart(
                prospect.name,
                prospect.city or "",
                phone=prospect.phone,
                social_url=prospect.social_url,
            )
            if found:
                data = prospect.model_dump()
                data["email"] = found
                confidence = validation_service.calculate_confidence_score(
                    phone=data.get("phone"),
                    address=data.get("address"),
                    email=found,
                    website=data.get("website"),
                )
                data["confidence"] = max(1, min(confidence, 4))
                return ProspectCreate(**data)
        except Exception as exc:
            logger.debug("[Auto] Email enrichment failed for %s: %s", prospect.name, exc)
        return prospect

    async def scrape(
        self,
        category: str,
        city: str,
        max_results: int = 50,
        *,
        only_without_website: bool = True,
        progress: ScrapeProgressReporter | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> list[ProspectCreate]:
        """
        Scrape prospects using OSM + Pages Jaunes in parallel then enrich emails.

        Args:
            category: Business category (``plombier``, ``electricien``, …).
            city: City to search in.
            max_results: Maximum prospects to return.
            only_without_website: When True, skip prospects with a website.
            progress: Optional SSE progress reporter.
            should_stop: Optional callback to abort early.

        Returns:
            Deduplicated, email-enriched list of prospects.
        """
        logger.info(
            "[Auto] Starting scrape category=%s city=%s max=%s",
            category,
            city,
            max_results,
        )
        await self.start()

        try:
            if progress:
                await progress.log("Auto — lancement OSM + Pages Jaunes en parallèle…")

            # Fetch more than needed to account for dedup & website filter
            fetch_max = max(max_results * 4, 20)

            osm_results, pj_results = await asyncio.gather(
                self._run_osm(category, city, fetch_max, only_without_website, progress, should_stop),
                self._run_pj(category, city, fetch_max, only_without_website, progress, should_stop),
            )

            osm_count = len(osm_results)
            pj_count = len(pj_results)
            logger.info("[Auto] Phase 1 done — OSM: %s  PagesJaunes: %s", osm_count, pj_count)

            if progress:
                await progress.log(f"Auto — OSM : {osm_count} résultat(s) · Pages Jaunes : {pj_count} résultat(s)")

            # Phase 2: merge + deduplicate
            # PagesJaunes results take priority (richer data: address, phone)
            merged: list[ProspectCreate] = []
            seen: set[str] = set()

            for prospect in list(pj_results) + list(osm_results):
                if should_stop and should_stop():
                    break
                key = self._normalize_name(prospect.name)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(prospect)

            logger.info("[Auto] After dedup: %s unique prospects", len(merged))

            if not merged:
                if progress:
                    await progress.log("Auto — aucun résultat trouvé.")
                return []

            if progress:
                await progress.log(f"Auto — enrichissement des emails ({len(merged)} prospect(s))…")

            enriched: list[ProspectCreate] = []
            for prospect in merged:
                if should_stop and should_stop():
                    break
                if len(enriched) >= max_results:
                    break

                prospect = await self._enrich_email(prospect)
                enriched.append(prospect)

                if progress:
                    await progress.prospect(prospect)

            logger.info("[Auto] Final: %s prospects returned", len(enriched))
            return enriched[:max_results]

        except Exception as exc:
            logger.error("[Auto] Unexpected error: %s", exc, exc_info=True)
            return []

        finally:
            await self.stop()
