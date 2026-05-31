"""Prospect enrichment from Google Maps."""
from __future__ import annotations

import logging
from typing import Optional

from models.prospect import ProspectCreate, ProspectSearchSuggestion
from scrappers.google_scraper import GoogleScraper

logger = logging.getLogger(__name__)


def format_scraper_error_message(exc: Exception) -> str:
    """Return an ASCII-safe, user-facing scraper error message."""
    raw_message: str = str(exc).strip()
    ascii_message: str = raw_message.encode("ascii", errors="ignore").decode("ascii").strip()

    if "nodriver is not installed" in raw_message.lower():
        return "nodriver n'est pas installé. Dans le dossier api : pip install nodriver"
    if "failed to start chrome" in raw_message.lower():
        return (
            "Chrome n'a pas pu démarrer via nodriver. "
            "Installez Google Chrome ou définissez SCRAPER_CHROME_EXECUTABLE."
        )
    if isinstance(exc, NotImplementedError) or exc.__class__.__name__ == "NotImplementedError":
        return (
            "Le navigateur ne peut pas démarrer sous ce serveur Windows. "
            "Redémarrez l'API avec : cd api && python run_dev.py"
        )
    if ascii_message:
        return ascii_message
    if raw_message:
        return raw_message
    return exc.__class__.__name__


class ProspectEnrichmentService:
    """Enrich a single prospect from Google Maps."""

    async def enrich_from_google(
        self,
        *,
        business_name: Optional[str] = None,
        google_maps_url: Optional[str] = None,
        city: Optional[str] = None,
    ) -> ProspectCreate:
        """
        Fetch prospect details from Google Maps using a place URL and/or business name.

        When both are provided, the Google Maps URL takes precedence.
        """
        cleaned_name: Optional[str] = business_name.strip() if business_name and business_name.strip() else None
        cleaned_url: Optional[str] = google_maps_url.strip() if google_maps_url and google_maps_url.strip() else None
        cleaned_city: Optional[str] = city.strip() if city and city.strip() else None

        if not cleaned_name and not cleaned_url:
            raise ValueError("Provide a business name and/or a Google Maps link.")

        scraper = GoogleScraper()
        prospect: Optional[ProspectCreate] = None

        try:
            if cleaned_url:
                prospect = await scraper.scrape_place_url(cleaned_url)
            elif cleaned_name:
                prospect = await scraper.scrape_by_business_name(cleaned_name, cleaned_city)
        except ValueError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Google Maps enrichment failed")
            raise ValueError(f"Google Maps enrichment failed: {format_scraper_error_message(exc)}") from exc

        if not prospect:
            raise ValueError(
                "No business found on Google Maps. Check the company name, city, or Google link."
            )

        return prospect

    async def search_suggestions(
        self,
        *,
        query: str,
        city: Optional[str] = None,
        max_results: int = 8,
    ) -> list[ProspectSearchSuggestion]:
        """Return Google Maps business suggestions for autocomplete."""
        cleaned_query: str = query.strip()
        if len(cleaned_query) < 2:
            raise ValueError("Search query must be at least 2 characters.")

        scraper = GoogleScraper()
        try:
            return await scraper.search_business_suggestions(
                cleaned_query,
                city,
                max_results=max_results,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Google Maps suggestion search failed")
            raise ValueError(f"Google Maps search failed: {format_scraper_error_message(exc)}") from exc


prospect_enrichment_service = ProspectEnrichmentService()
