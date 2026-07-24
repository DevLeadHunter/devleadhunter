"""
Google Maps scraper for fetching business prospects (nodriver).
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import TypeVar
from urllib.parse import quote

from enums.source import Source
from models.prospect import ProspectCreate, ProspectSearchSuggestion
from scrappers import scrape_signals
from scrappers.nodriver_browser import NODRIVER_AVAILABLE, NodriverBrowser, NodriverScraperMixin
from scrappers.nodriver_dom import NodriverDom
from scrappers.nodriver_executor import run_nodriver_task
from scrappers.resilient_extract import find_phone, parse_ld_json_blocks
from services.scrape_progress import ScrapeProgressReporter
from services.validation_service import validation_service

from .base_scraper import BaseScraper
from .email_scraper import email_scraper

logger = logging.getLogger(__name__)

T = TypeVar("T")

SUGGESTION_CACHE_TTL_SECONDS = 300

_suggestion_cache: dict[str, tuple[float, list[ProspectSearchSuggestion]]] = {}


@dataclass
class _MapsSuggestionSession:
    browser: NodriverBrowser
    tab: object
    search_lock: asyncio.Lock


_maps_suggestion_session: _MapsSuggestionSession | None = None


def _suggestion_cache_key(query: str, city: str | None, max_results: int) -> str:
    return f"{query.strip().lower()}|{(city or '').strip().lower()}|{max_results}"


def _read_suggestion_cache(key: str) -> list[ProspectSearchSuggestion] | None:
    entry = _suggestion_cache.get(key)
    if not entry:
        return None
    cached_at, results = entry
    if monotonic() - cached_at > SUGGESTION_CACHE_TTL_SECONDS:
        _suggestion_cache.pop(key, None)
        return None
    return results


def _write_suggestion_cache(key: str, results: list[ProspectSearchSuggestion]) -> None:
    _suggestion_cache[key] = (monotonic(), results)


async def _ensure_maps_suggestion_session() -> _MapsSuggestionSession:
    """Reuse one browser tab for autocomplete searches (cookies accepted once)."""
    global _maps_suggestion_session

    if _maps_suggestion_session is not None:
        return _maps_suggestion_session

    browser = NodriverBrowser(ephemeral=True)
    tab = await browser.get_tab("https://www.google.com/maps")
    scraper = GoogleScraper()
    await scraper._prepare_maps_tab(tab)

    _maps_suggestion_session = _MapsSuggestionSession(
        browser=browser,
        tab=tab,
        search_lock=asyncio.Lock(),
    )
    return _maps_suggestion_session


async def warmup_maps_suggestion_session() -> None:
    """Pre-open Chrome so the first autocomplete query is faster."""
    if not NODRIVER_AVAILABLE:
        return
    await _ensure_maps_suggestion_session()


class GoogleScraper(NodriverScraperMixin, BaseScraper):
    """
    Google Maps scraper for extracting business prospect data.

    Uses nodriver (Chrome CDP) to interact with Google Maps and extract
    business information including name, address, phone, website, and category.
    """

    def __init__(self) -> None:
        super().__init__(source=Source.GOOGLE)
        self._init_nodriver()

    @staticmethod
    async def accept_cookies(tab: object) -> bool:
        """
        Accept cookies on Google Maps.

        Args:
            tab: nodriver Tab instance.

        Returns:
            True if cookies were accepted, False otherwise.
        """
        selectors = [
            'button[aria-label*="Tout accepter"]',
            'button[jsname="j6LkBc"]',
            'input[value="Tout accepter"]',
        ]
        try:
            if await NodriverDom.click_first_matching(tab, selectors):
                logger.info("Cookies accepted")
                await asyncio.sleep(0.5)
                return True
            if await NodriverDom.click_by_text(tab, "button", "Tout accepter"):
                await asyncio.sleep(0.5)
                return True
            if await NodriverDom.click_by_text(tab, "button", "Accept all"):
                await asyncio.sleep(0.5)
                return True
            return False
        except Exception as exc:
            logger.error("Error accepting cookies: %s", exc)
            return False

    @staticmethod
    async def accept_web_modal(tab: object) -> bool:
        """
        Accept the "Stay on web" modal on Google Maps.

        Args:
            tab: nodriver Tab instance.

        Returns:
            True if the modal was accepted, False otherwise.
        """
        try:
            if await NodriverDom.wait_for_selector(tab, '[class*="qgMOee"]', timeout_s=5.0):
                await NodriverDom.click(tab, '[class*="qgMOee"]')
                logger.info("Web modal accepted")
                await asyncio.sleep(0.5)
                return True
            return False
        except Exception as exc:
            logger.error("Error accepting web modal: %s", exc)
            return False

    @staticmethod
    def build_query(category: str | None, city: str | None) -> str:
        """Build a URL-encoded Google Maps search query."""
        parts: list[str] = []
        if category:
            parts.append(category)
        if city:
            parts.append(f"à {city}")
        query = " ".join(parts).strip()
        return quote(query) if query else "entreprises"

    @staticmethod
    def _sanitize_maps_text(text: str) -> str:
        """Remove Maps icon glyphs and normalize whitespace."""
        if not text:
            return ""
        cleaned = re.sub(r"[\uE000-\uF8FF]", "", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @staticmethod
    def extract_city(address: str) -> str:
        """Extract city name from a full address string."""
        address = GoogleScraper._sanitize_maps_text(address)
        if not address:
            return "Inconnue"
        postal_match = re.search(r"\b(\d{5})\s+(.+)$", address)
        if postal_match:
            return postal_match.group(2).strip()
        parts = [p.strip() for p in address.split(",") if p.strip()]
        if len(parts) >= 2:
            return parts[-1]
        return parts[-1] if parts else "Inconnue"

    @staticmethod
    def normalize_maps_url(url: str) -> str:
        """Normalize a Google Maps share or place URL."""
        normalized = url.strip()
        if not normalized:
            return normalized
        if not normalized.startswith("http"):
            normalized = f"https://{normalized}"
        return normalized

    @staticmethod
    def is_maps_url(url: str) -> bool:
        """Return True when the URL looks like a Google Maps link."""
        lowered = url.lower()
        if "goo.gl" in lowered:
            return True
        return "google." in lowered and "maps" in lowered

    @staticmethod
    def _is_valid_place_name(name: str) -> bool:
        """Return False for feed chrome labels that are not business names."""
        lowered = name.strip().lower()
        if not lowered or len(lowered) < 2:
            return False
        return lowered not in {"résultats", "results", "resultats"}

    @staticmethod
    def build_business_query(business_name: str, city: str | None = None) -> str:
        """Build a Google Maps search query for a business name."""
        parts: list[str] = [business_name.strip()]
        if city and city.strip():
            parts.append(city.strip())
        return quote(" ".join(parts))

    async def _prepare_maps_tab(self, tab: object) -> None:
        """Accept cookies and optional web modal on a Maps tab."""
        await self.accept_cookies(tab)
        await self.accept_web_modal(tab)

    async def _navigate_to_maps_url(self, tab: object, url: str, *, place_timeout_s: float = 20.0) -> str:
        """Open a Google Maps URL and wait until the place panel is ready."""
        logger.info("Navigating to Google Maps URL: %s", url)
        try:
            await NodriverDom.navigate(tab, url, sleep_s=1.0)
        except Exception as exc:
            raise ValueError(
                "Google Maps page load timed out. Retry or paste the full google.com/maps/place link."
            ) from exc

        await self._prepare_maps_tab(tab)

        current_url = NodriverDom.tab_url(tab)
        if "consent.google" in current_url:
            await self._prepare_maps_tab(tab)
            await NodriverDom.navigate(tab, url, sleep_s=1.0)
            await self._prepare_maps_tab(tab)

        final_url = NodriverDom.tab_url(tab)
        if "/maps/place/" not in final_url and "/maps/search/" not in final_url:
            raise ValueError("This Google Maps link does not open a business page.")

        if not await NodriverDom.wait_for_selector(tab, "h1", timeout_s=place_timeout_s):
            raise ValueError("Google Maps business details could not be loaded from this link.")

        return final_url

    async def _extract_current_place(
        self,
        tab: object,
        *,
        default_category: str = "Entreprise",
        item_timeout_s: float = 5.0,
    ) -> dict[str, str | None] | None:
        """Extract business details from the currently open Google Maps place panel.

        Resilient to Google's obfuscated-class churn: each field tries its current
        selector first, then known alternates (``aria-label`` / ``data-*``), and finally
        falls back to any JSON-LD on the page. A field going missing degrades that field
        only — it never breaks the record (only a missing ``name`` is fatal).
        """
        try:
            if not await NodriverDom.wait_for_selector(tab, "h1", timeout_s=item_timeout_s):
                return None

            # Layer 1 — current selector, then semantic / data-* alternates.
            name = await NodriverDom.inner_text_chain(tab, ["h1", "[role='main'] h1"])
            address = (
                await NodriverDom.inner_text_chain(
                    tab,
                    [
                        "[data-item-id='address']",
                        "button[data-item-id='address']",
                        "[data-item-id^='address']",
                        "button[aria-label*='Adresse']",
                        "button[aria-label*='Address']",
                    ],
                )
                or ""
            )
            phone = await NodriverDom.inner_text_chain(
                tab,
                [
                    "[data-item-id='phone']",
                    "[data-item-id^='phone']",
                    "button[aria-label*='Téléphone']",
                    "button[aria-label*='Phone']",
                ],
            )
            website = await NodriverDom.get_attribute_chain(
                tab,
                [
                    "a[data-item-id='authority']",
                    "a[data-item-id^='authority']",
                    "a[aria-label*='site Web']",
                    "a[aria-label*='website']",
                ],
                "href",
            )
            category = (
                await NodriverDom.inner_text_chain(
                    tab,
                    [
                        "button[data-value='Main category']",
                        "button[jsaction*='category']",
                        "[data-item-id='category']",
                    ],
                )
                or default_category
            )

            # Layer 2 — JSON-LD fallback for anything still missing.
            if not (name and phone and address and website):
                business = parse_ld_json_blocks(await NodriverDom.ld_json_blocks(tab))
                if business:
                    name = name or business.get("name")
                    phone = phone or business.get("phone")
                    address = address or business.get("street") or ""
                    website = website or business.get("website")
                    if category == default_category and business.get("category"):
                        category = business["category"]

            name = self._sanitize_maps_text(name)
            address = self._sanitize_maps_text(address)
            phone = self._sanitize_maps_text(phone) if phone else None
            category = self._sanitize_maps_text(category) if category else default_category

            if not name:
                return None

            # Layer 3 — regex-normalise the phone (markup-independent); keep raw if no match.
            phone = find_phone(phone) or (phone.strip() if phone else None)

            city_name = self.extract_city(address)
            return {
                "name": name.strip(),
                "address": address.strip(),
                "city": city_name,
                "phone": phone,
                "website": website,
                "category": category.strip(),
            }
        except Exception as exc:
            logger.error("Failed to extract Google Maps place details: %s", exc)
            return None

    async def _build_prospect_from_details(self, details: dict[str, str | None]) -> ProspectCreate:
        """Build a ProspectCreate object from extracted Maps details."""
        name = details["name"] or "Entreprise"
        address = details.get("address") or ""
        city = details.get("city") or "Inconnue"
        phone = details.get("phone")
        website = details.get("website")
        category = details.get("category") or "Entreprise"

        confidence = validation_service.calculate_confidence_score(
            phone=phone,
            address=address,
            website=website,
        )

        email: str | None = None
        try:
            email = await email_scraper.find_email(name, city)
        except Exception as exc:
            logger.debug("Could not find email for %s: %s", name, exc)

        return ProspectCreate(
            name=name,
            address=address or None,
            city=city,
            phone=phone,
            email=email,
            website=website,
            category=category,
            source=Source.GOOGLE,
            confidence=confidence,
        )

    async def scrape_place_url(self, url: str) -> ProspectCreate | None:
        """Scrape a single Google Maps place from a direct business URL."""
        if not NODRIVER_AVAILABLE:
            logger.warning("nodriver not available, cannot enrich from Google Maps URL")
            return None

        normalized_url = self.normalize_maps_url(url)
        if not self.is_maps_url(normalized_url):
            raise ValueError("Invalid Google Maps URL.")

        scraper = GoogleScraper()

        async def task() -> ProspectCreate | None:
            return await scraper._scrape_place_url_nodriver(normalized_url)

        return await run_nodriver_task(task, timeout=120)

    async def _scrape_place_url_nodriver(self, normalized_url: str) -> ProspectCreate | None:
        """nodriver implementation for scraping a Google Maps place URL."""
        await self.start()
        try:
            tab = await self._nodriver.get_tab()
            try:
                await self._navigate_to_maps_url(tab, normalized_url, place_timeout_s=8.0)
                details = await self._extract_current_place(tab, item_timeout_s=8.0)
                if not details or not details.get("name"):
                    return None
                return await self._build_prospect_from_details(details)
            finally:
                pass
        finally:
            await self.stop()
            await self.close()

    @staticmethod
    def _parse_suggestion_label(raw_label: str) -> tuple[str, str | None]:
        """Split a Google Maps aria-label into business name and address."""
        cleaned = " ".join(raw_label.split())
        if not cleaned:
            return "Entreprise", None
        if " · " in cleaned:
            name, address = cleaned.split(" · ", 1)
            return name.strip(), address.strip() or None
        return cleaned, None

    @staticmethod
    def _normalize_maps_href(href: str) -> str:
        """Convert a Google Maps href into an absolute URL."""
        if href.startswith("http://") or href.startswith("https://"):
            return href
        if href.startswith("/"):
            return f"https://www.google.com{href}"
        return f"https://www.google.com/maps/place/{href}"

    @staticmethod
    def _build_search_suggestion(
        *,
        label: str,
        google_maps_url: str,
        description: str | None = None,
    ) -> ProspectSearchSuggestion:
        """Build a typed Google Maps search suggestion."""
        return ProspectSearchSuggestion(
            id=google_maps_url,
            label=label,
            description=description,
            google_maps_url=google_maps_url,
        )

    async def search_business_suggestions(
        self,
        query: str,
        city: str | None = None,
        max_results: int = 8,
    ) -> list[ProspectSearchSuggestion]:
        """Search Google Maps and return lightweight business suggestions."""
        if not NODRIVER_AVAILABLE:
            logger.warning("nodriver not available, cannot search business suggestions")
            return []

        cleaned_query = query.strip()
        if len(cleaned_query) < 2:
            return []

        scraper = GoogleScraper()

        async def task() -> list[ProspectSearchSuggestion]:
            return await scraper._search_business_suggestions_nodriver(cleaned_query, city, max_results)

        return await run_nodriver_task(task, timeout=120)

    async def _search_business_suggestions_nodriver(
        self,
        cleaned_query: str,
        city: str | None,
        max_results: int,
    ) -> list[ProspectSearchSuggestion]:
        """nodriver implementation for Google Maps business suggestions."""
        cache_key = _suggestion_cache_key(cleaned_query, city, max_results)
        cached = _read_suggestion_cache(cache_key)
        if cached is not None:
            return cached

        session = await _ensure_maps_suggestion_session()
        async with session.search_lock:
            cached = _read_suggestion_cache(cache_key)
            if cached is not None:
                return cached

            tab = session.tab
            search_query = self.build_business_query(cleaned_query, city)
            url = f"https://www.google.com/maps/search/{search_query}"
            logger.info("Searching Google Maps suggestions: %s", url)
            await NodriverDom.navigate(tab, url, sleep_s=0.8)

            if not await NodriverDom.wait_for_selector(tab, "div[role='feed']", timeout_s=6.0):
                single = await self._extract_current_place(tab, default_category="Entreprise", item_timeout_s=3.0)
                if single and single.get("name"):
                    maps_url = NodriverDom.tab_url(tab)
                    suggestions = [
                        self._build_search_suggestion(
                            label=single["name"],
                            google_maps_url=maps_url,
                            description=single.get("address") or single.get("city"),
                        )
                    ]
                    _write_suggestion_cache(cache_key, suggestions)
                    return suggestions
                _write_suggestion_cache(cache_key, [])
                return []

            link_data = await NodriverDom.evaluate_list(
                tab,
                """
                (() => Array.from(document.querySelectorAll("div[role='feed'] a[href*='/maps/place/']"))
                    .map(a => ({
                        href: a.getAttribute('href'),
                        label: (a.getAttribute('aria-label') || a.innerText || '').trim()
                    }))
                    .filter(x => x.href && x.label))()
                """,
            )

            suggestions: list[ProspectSearchSuggestion] = []
            seen_urls: set[str] = set()

            for item in link_data[: max_results + 4]:
                if len(suggestions) >= max_results:
                    break
                if not isinstance(item, dict):
                    continue
                href = str(item.get("href") or "")
                raw_label = str(item.get("label") or "").strip()
                if not href or href in seen_urls or not raw_label:
                    continue
                seen_urls.add(href)
                name, address = self._parse_suggestion_label(raw_label)
                suggestions.append(
                    self._build_search_suggestion(
                        label=name,
                        google_maps_url=self._normalize_maps_href(href),
                        description=address,
                    )
                )

            _write_suggestion_cache(cache_key, suggestions)
            return suggestions

    async def scrape_by_business_name(
        self,
        business_name: str,
        city: str | None = None,
    ) -> ProspectCreate | None:
        """Find a business on Google Maps by name and scrape its public details."""
        if not NODRIVER_AVAILABLE:
            logger.warning("nodriver not available, cannot enrich from business name")
            return None

        cleaned_name = business_name.strip()
        if not cleaned_name:
            raise ValueError("Business name is required.")

        scraper = GoogleScraper()

        async def task() -> ProspectCreate | None:
            return await scraper._scrape_by_business_name_nodriver(cleaned_name, city)

        return await run_nodriver_task(task, timeout=120)

    async def _scrape_by_business_name_nodriver(
        self,
        cleaned_name: str,
        city: str | None,
    ) -> ProspectCreate | None:
        """nodriver implementation for enriching a prospect by business name."""
        await self.start()
        try:
            tab = await self._nodriver.get_tab()
            try:
                query = self.build_business_query(cleaned_name, city)
                url = f"https://www.google.com/maps/search/{query}"
                logger.info("Enriching prospect from Google Maps search: %s", url)
                await NodriverDom.navigate(tab, url, sleep_s=1.0)
                await self._prepare_maps_tab(tab)

                details = await self._extract_current_place(tab, default_category="Entreprise", item_timeout_s=4.0)
                if details and details.get("name"):
                    return await self._build_prospect_from_details(details)

                if not await NodriverDom.wait_for_selector(tab, "div[role='feed']", timeout_s=10.0):
                    return None

                clicked = await NodriverDom.evaluate(
                    tab,
                    """
                    (() => {
                        const link = document.querySelector("div[role='feed'] a[href*='/maps/place/']");
                        if (!link) return false;
                        link.removeAttribute('target');
                        link.click();
                        return true;
                    })()
                    """,
                    by_value=True,
                )
                if clicked is not True:
                    return None

                await asyncio.sleep(1.0)
                details = await self._extract_current_place(tab, default_category="Entreprise", item_timeout_s=8.0)
                if not details or not details.get("name"):
                    return None
                return await self._build_prospect_from_details(details)
            finally:
                pass
        finally:
            await self.stop()
            await self.close()

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
        Scrape prospects from Google Maps.

        Args:
            category: Business category to search for.
            city: City to search in.
            max_results: Maximum number of results to return.

        Returns:
            List of ProspectCreate objects.
        """
        if not NODRIVER_AVAILABLE:
            logger.warning("nodriver not available, returning empty results")
            return []

        async def task() -> list[ProspectCreate]:
            return await self._scrape_nodriver(category, city, max_results, only_without_website, progress, should_stop)

        return await run_nodriver_task(task, timeout=600)

    async def _scrape_nodriver(
        self,
        category: str,
        city: str,
        max_results: int,
        only_without_website: bool,
        progress: ScrapeProgressReporter | None,
        should_stop: Callable[[], bool] | None,
    ) -> list[ProspectCreate]:
        """nodriver bulk scrape implementation."""
        await self.start()
        try:
            tab = await self._nodriver.get_tab()
            try:
                if progress:
                    await progress.log("Google Maps — chargement de la recherche…")
                query = self.build_query(category, city)
                url = f"https://www.google.com/maps/search/{query}"
                logger.info("Scraping: %s", url)
                await NodriverDom.navigate(tab, url, sleep_s=0.6)
                await self._prepare_maps_tab(tab)

                feed_selector = "motion.div[role='feed'], div[role='feed']"
                if not await NodriverDom.wait_for_selector(tab, feed_selector, timeout_s=12.0):
                    logger.warning(
                        "Maps feed not found (url=%s) — trying single-place panel",
                        NodriverDom.tab_url(tab),
                    )
                    single = await self._extract_current_place(tab, default_category=category, item_timeout_s=4.0)
                    if single and single.get("name") and self._is_valid_place_name(single["name"]):
                        if only_without_website and single.get("website"):
                            return []
                        prospect = await self._build_prospect_from_details(single)
                        if progress:
                            await progress.prospect(prospect)
                        return [prospect]
                    logger.error("No feed and no single place — page may be blocked or consent pending")
                    try:
                        page_html = await NodriverDom.evaluate(tab, "document.documentElement.outerHTML", by_value=True)
                    except Exception:
                        page_html = None
                    scrape_signals.note_block(
                        self.source.value,
                        reason="no feed (blocked or consent pending)",
                        html=page_html if isinstance(page_html, str) else None,
                    )
                    return []

                place_hrefs: list[str] = []
                seen_urls: set[str] = set()
                scroll_attempts = 0
                max_scrolls = 8
                href_target = max(max_results * (8 if only_without_website else 2), max_results)

                while len(place_hrefs) < href_target and scroll_attempts < max_scrolls:
                    hrefs = await NodriverDom.evaluate_list(
                        tab,
                        """
                        (() => Array.from(document.querySelectorAll("motion.div[role='feed'] a[href*='/maps/place/'], div[role='feed'] a[href*='/maps/place/']"))
                            .map(a => a.getAttribute('href'))
                            .filter(Boolean))()
                        """,
                    )
                    for href in hrefs:
                        if isinstance(href, str) and href and href not in seen_urls:
                            seen_urls.add(href)
                            place_hrefs.append(href)
                    if len(place_hrefs) >= href_target:
                        break
                    await NodriverDom.scroll_element(tab, feed_selector, 2500)
                    await asyncio.sleep(0.15)
                    scroll_attempts += 1

                logger.info("Collected %s place links from Google Maps feed", len(place_hrefs))
                if progress:
                    await progress.log(f"Google Maps — {len(place_hrefs)} fiche(s) à analyser")

                prospects: list[ProspectCreate] = []
                max_to_open = max(max_results * (12 if only_without_website else 2), max_results)

                for href in place_hrefs[:max_to_open]:
                    if should_stop and should_stop():
                        break
                    if len(prospects) >= max_results:
                        break

                    place_url = self._normalize_maps_href(href)
                    await NodriverDom.navigate(tab, place_url, sleep_s=0.35)

                    details = await self._extract_current_place(tab, default_category=category, item_timeout_s=3.0)
                    if not details or not details.get("name"):
                        continue
                    if not self._is_valid_place_name(details["name"]):
                        continue

                    name = details["name"]
                    address = details.get("address") or ""
                    phone = details.get("phone")
                    website = details.get("website")
                    if only_without_website and website:
                        continue

                    extracted_category = details.get("category") or category
                    city_name = details.get("city") or self.extract_city(address)

                    confidence = validation_service.calculate_confidence_score(
                        phone=phone,
                        address=address,
                        website=website,
                    )

                    email: str | None = None
                    try:
                        email = await email_scraper.find_email(name, city_name)
                    except Exception as exc:
                        logger.debug("Could not find email: %s", exc)

                    prospects.append(
                        ProspectCreate(
                            name=name,
                            address=address,
                            city=city_name,
                            phone=phone,
                            email=email,
                            website=website,
                            category=extracted_category,
                            source=Source.GOOGLE,
                            confidence=confidence,
                        )
                    )
                    if progress:
                        await progress.prospect(prospects[-1])

                logger.info("Scraping complete: %s prospects found", len(prospects))
                return prospects
            except Exception as exc:
                logger.error("Error in Google scraping: %s", exc)
                return []
        finally:
            await self.stop()
            await self.close()
