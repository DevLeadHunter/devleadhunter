"""
BrightData scraper: PagesJaunes discovery + Google email search via BrightData HTTP API.

Strategy
--------
1. Fetch the PagesJaunes listing page for the given category + city via Web Unlocker.
2. Parse the HTML to extract detail-page URLs (/pros/<id>).
3. For each detail URL, fetch and parse: name, phone, address, website.
4. Skip prospects that already have a website when ``only_without_website=True``.
5. For each qualifying prospect, run a tiered Google SERP email search:
   a. ``"{name}" "{phone}"``     — most targeted (finds guide-artisan.fr, RGE, etc.)
   b. ``"{name}" "{city}" email``— city-scoped search
   c. ``{name} {city} contact email`` — broad fallback
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import unicodedata
from typing import Callable, List, Optional
from urllib.parse import quote_plus, urljoin

import aiohttp
from bs4 import BeautifulSoup

from enums.source import Source
from models.prospect import ProspectCreate
from services.scrape_progress import ScrapeProgressReporter
from services.validation_service import validation_service

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# BrightData Web Unlocker API endpoint
_BRIGHTDATA_REQUEST_URL: str = "https://api.brightdata.com/request"

# PagesJaunes category slug mapping
_PJ_CATEGORY_MAP: dict[str, str] = {
    "plombier": "plombiers",
    "restaurant": "restaurants",
    "coiffeur": "coiffeurs",
    "electricien": "electriciens",
    "garage": "garages-auto",
}

# Email spam filter: domains and local-part prefixes that are never real prospects
_SPAM_DOMAINS: frozenset[str] = frozenset(
    {
        "example.com",
        "test.com",
        "domain.com",
        "yoursite.com",
        "google.com",
        "gstatic.com",
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "linkedin.com",
        "youtube.com",
        "tiktok.com",
        "eldo.com",
        "avis-verifies.com",
        "trustpilot.com",
        "tripadvisor.com",
        "tripadvisor.fr",
        "yelp.com",
        "yelp.fr",
        "plombiers.com",
        "electriciens.com",
        "artisans.com",
        "pagesjaunes.fr",
        "pages-jaunes.fr",
        "annuaire.com",
        "annuaires.com",
        "kompass.com",
        "societe.com",
        "verif.com",
        "infogreffe.fr",
        "geneafrance.com",
        "geneanet.org",
        "filae.com",
    }
)
_SPAM_PREFIXES: tuple[str, ...] = (
    "u003",
    "u0022",
    "noreply",
    "no-reply",
    "donotreply",
    "service-avis",
    "mairie",
)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


def _is_valid_email(addr: str) -> bool:
    """
    Return True if *addr* is not a known spam / placeholder email.

    Args:
        addr: Email address to validate.

    Returns:
        True when the address is not on the spam blocklist.
    """
    low = addr.lower()
    if any(sp in low for sp in _SPAM_DOMAINS):
        return False
    local = low.split("@")[0]
    return not any(local.startswith(pfx) for pfx in _SPAM_PREFIXES)


def _extract_valid_emails(text: str) -> list[str]:
    """
    Extract all non-spam email addresses from *text*.

    Args:
        text: Raw text (HTML or plain) to scan.

    Returns:
        De-duplicated list of valid email addresses.
    """
    seen: set[str] = set()
    result: list[str] = []
    for addr in _EMAIL_RE.findall(text):
        low = addr.lower()
        if low not in seen and _is_valid_email(low):
            seen.add(low)
            result.append(addr)
    return result


def _normalize_phone(phone: str) -> str:
    """
    Format a French phone number as ``"XX XX XX XX XX"`` (pairs of digits).

    Handles both ``+33`` and ``0``-prefixed formats.

    Args:
        phone: Raw phone string (may contain spaces, dots, dashes).

    Returns:
        Formatted phone string, or the stripped input if format is unrecognised.
    """
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("33") and len(digits) == 11:
        digits = "0" + digits[2:]
    if len(digits) == 10:
        return " ".join(digits[i: i + 2] for i in range(0, 10, 2))
    return phone.strip()


def _city_to_pj_slug(city: str) -> str:
    """
    Convert a city name to the slug format used in PagesJaunes URLs.

    Args:
        city: City name (e.g. ``"Bédée"``).

    Returns:
        Lowercase, accent-free, hyphen-separated slug (e.g. ``"bedee"``).
    """
    nfd = unicodedata.normalize("NFD", city.lower())
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]+", "-", stripped).strip("-")


class BrightDataScraper(BaseScraper):
    """
    Scraper that routes all HTTP calls through the BrightData Web Unlocker API.

    Unlike Chrome-based scrapers this class is purely async HTTP — no browser
    process is spawned — making it lightweight and easy to parallelize.

    The scraping strategy mirrors what the AutoScraper (OSM + PagesJaunes)
    does, but every request passes through BrightData's proxy infrastructure
    to bypass bot-detection on PagesJaunes and Google.
    """

    def __init__(self) -> None:
        """Initialize the scraper and load BrightData credentials from settings."""
        super().__init__(source=Source.BRIGHTDATA)
        self._token: str = self._load_token()
        self._zone: str = self._load_zone()

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_token() -> str:
        """
        Load the BrightData API token from application settings or environment.

        Returns:
            API token string, or empty string when not configured.
        """
        try:
            from core.config import settings  # local import — avoids circular deps

            return settings.brightdata_api_token or ""
        except Exception:  # noqa: BLE001
            import os

            return os.environ.get("BRIGHTDATA_API_TOKEN", "")

    @staticmethod
    def _load_zone() -> str:
        """
        Load the BrightData zone name from application settings or environment.

        Returns:
            Zone name string, defaulting to ``"mcp_unlocker"``.
        """
        try:
            from core.config import settings

            return settings.brightdata_zone or "mcp_unlocker"
        except Exception:  # noqa: BLE001
            import os

            return os.environ.get("BRIGHTDATA_ZONE", "mcp_unlocker")

    # ------------------------------------------------------------------
    # HTTP layer
    # ------------------------------------------------------------------

    async def _fetch(self, url: str, *, zone: Optional[str] = None) -> str:
        """
        Fetch *url* via the BrightData Web Unlocker API and return raw HTML.

        Args:
            url: Target URL to retrieve.
            zone: BrightData zone name override (defaults to ``self._zone``).

        Returns:
            Raw HTML content of the response.

        Raises:
            aiohttp.ClientResponseError: When the API returns a non-2xx status.
            aiohttp.ClientConnectorError: On network-level failures.
        """
        payload = {
            "zone": zone or self._zone,
            "url": url,
            "format": "raw",
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                _BRIGHTDATA_REQUEST_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=90),
            ) as resp:
                resp.raise_for_status()
                return await resp.text()

    # ------------------------------------------------------------------
    # PagesJaunes — listing page
    # ------------------------------------------------------------------

    async def _scrape_pj_listing(
        self,
        category: str,
        city: str,
        max_count: int,
    ) -> list[str]:
        """
        Fetch the PagesJaunes listing page and return up to *max_count* detail URLs.

        Args:
            category: Business category key (``"plombier"``, ``"electricien"``, …).
            city: City name (e.g. ``"Bédée"``).
            max_count: Maximum number of detail-page URLs to return.

        Returns:
            List of absolute PagesJaunes detail-page URLs (``/pros/<id>``).
        """
        cat_slug = _PJ_CATEGORY_MAP.get(category.lower(), f"{category.lower()}s")
        city_slug = _city_to_pj_slug(city)
        listing_url = f"https://www.pagesjaunes.fr/annuaire/{city_slug}/{cat_slug}"

        logger.info("[BrightData] Fetching PJ listing: %s", listing_url)
        try:
            html = await self._fetch(listing_url)
        except Exception as exc:  # noqa: BLE001
            logger.error("[BrightData] PJ listing fetch failed: %s", exc)
            return []

        soup = BeautifulSoup(html, "html.parser")
        seen: set[str] = set()
        urls: list[str] = []

        # Method 1: direct /pros/<id> href links
        for a_tag in soup.find_all("a", href=True):
            href: str = a_tag["href"]
            # Strip query strings to avoid duplicates
            clean = href.split("?")[0]
            if re.search(r"/pros/\d+$", clean) and clean not in seen:
                seen.add(clean)
                full = clean if clean.startswith("http") else urljoin("https://www.pagesjaunes.fr", clean)
                urls.append(full)
                if len(urls) >= max_count:
                    return urls

        # Method 2: base64-encoded links in data-pjlb attributes (PJ's obfuscation)
        for a_tag in soup.find_all("a", attrs={"data-pjlb": True}):
            raw_attr: str = a_tag["data-pjlb"].replace("&quot;", '"')
            try:
                data = json.loads(raw_attr)
                encoded_url: str = data.get("url", "")
                decoded = base64.b64decode(encoded_url).decode("utf-8").lstrip("/")
                if "pros/" in decoded:
                    full = urljoin("https://www.pagesjaunes.fr/", decoded)
                    clean = full.split("?")[0]
                    if clean not in seen:
                        seen.add(clean)
                        urls.append(clean)
                        if len(urls) >= max_count:
                            return urls
            except Exception:  # noqa: BLE001
                continue

        logger.info(
            "[BrightData] Extracted %d detail URLs for %s / %s",
            len(urls),
            category,
            city,
        )
        return urls

    # ------------------------------------------------------------------
    # PagesJaunes — detail page
    # ------------------------------------------------------------------

    async def _scrape_pj_detail(
        self,
        url: str,
        category: str,
        city: str,
    ) -> Optional[ProspectCreate]:
        """
        Fetch and parse a PagesJaunes detail page.

        Args:
            url: Absolute URL to the detail page.
            category: Business category label (stored on the prospect).
            city: Fallback city value when the address cannot be parsed.

        Returns:
            Populated :class:`ProspectCreate` instance, or ``None`` when
            the page could not be parsed (missing name).
        """
        try:
            html = await self._fetch(url)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[BrightData] Detail fetch failed (%s): %s", url, exc)
            return None

        soup = BeautifulSoup(html, "html.parser")

        # -- Name --
        name = ""
        for sel in ("h1.noTrad", "h1.denomination", "h1"):
            el = soup.select_one(sel)
            if el:
                # Take only the direct text node (ignore child spans like rating badges)
                name = el.find(string=True, recursive=False) or el.get_text(" ", strip=True)
                name = name.strip().split("\n")[0].strip()
                if name:
                    break
        if not name:
            return None

        # -- Phone --
        phone = ""
        for sel in ("span.coord-numero.noTrad", "span.coord-numero", ".num-container span"):
            el = soup.select_one(sel)
            if el:
                candidate = el.get_text(strip=True)
                if re.search(r"\d{8,}", re.sub(r"\s", "", candidate)):
                    phone = re.sub(r"\s+", " ", candidate).strip()
                    break
        if not phone:
            # Fallback: look for tel: href
            for a_tag in soup.find_all("a", href=re.compile(r"^tel:")):
                digits = re.sub(r"\D", "", a_tag["href"])
                if len(digits) >= 9:
                    phone = _normalize_phone(digits)
                    break

        # -- Address --
        address = ""
        for sel in (
            "a.black-icon.teaser-item span.noTrad",
            ".address.streetAddress",
            "#blocCoordonnees a.black-icon span.noTrad",
            "span.address",
        ):
            el = soup.select_one(sel)
            if el:
                address = el.get_text(" ", strip=True)
                break
        if not address:
            # Generic fallback: find text that contains a 5-digit postal code
            for el in soup.find_all(string=re.compile(r"\b\d{5}\b")):
                candidate = str(el).strip()
                if len(candidate) > 8:
                    address = candidate
                    break

        # -- City from address --
        city_found = city
        if address:
            m = re.search(r"\b(\d{5})\s+([\w\s\-']+)", address)
            if m:
                city_found = m.group(2).strip().title()
            try:
                from services.address_service import address_service

                address = address_service.remove_city_and_postal_code(address, city_found)
            except Exception:  # noqa: BLE001
                pass

        # -- Website and social URL --
        # Many PJ businesses list their Facebook/Instagram page as their "website".
        # We capture that separately as a transient social_url so email enrichment
        # can navigate directly to the profile instead of searching Google for it.
        website = ""
        social_url: Optional[str] = None
        for sel in (".MINISITE.pj-link", ".SITE_EXTERNE.pj-link", "a.MINISITE", "a.SITE_EXTERNE"):
            el = soup.select_one(sel)
            if not el:
                continue
            href = el.get("href", "") or ""
            if not href or href == "#":
                # BrightData sometimes renders the href as a data attribute
                raw_attr = el.get("data-pjlb", "").replace("&quot;", '"')
                if raw_attr:
                    try:
                        data = json.loads(raw_attr)
                        encoded = data.get("url", "")
                        href = base64.b64decode(encoded).decode("utf-8")
                    except Exception:  # noqa: BLE001
                        pass
            if not href or not href.startswith("http"):
                continue
            try:
                from services.validation_service import validation_service as vs

                if vs.is_valid_website(href):
                    website = href
                    break
                # Not a valid business website — save social profile URL for email enrichment
                href_low = href.lower()
                if social_url is None and (
                    "facebook.com/" in href_low or "instagram.com/" in href_low
                ):
                    social_url = href
                    logger.debug("[BrightData] Social URL for '%s': %s", name, href)
            except Exception:  # noqa: BLE001
                website = href
                break

        confidence = validation_service.calculate_confidence_score(
            phone=phone or None,
            address=address or None,
            email=None,
            website=website or None,
        )

        return ProspectCreate(
            name=name,
            address=address or None,
            city=city_found,
            phone=phone or None,
            email=None,
            website=website or None,
            category=category,
            source=Source.BRIGHTDATA,
            confidence=max(1, min(confidence, 4)),
            social_url=social_url,
        )

    # ------------------------------------------------------------------
    # Email enrichment via Google SERP
    # ------------------------------------------------------------------

    async def _fetch_social_email(self, social_url: str, name: str) -> Optional[str]:
        """
        Extract an email address from a Facebook or Instagram profile via BrightData.

        For Facebook the ``/about`` sub-page is fetched because it exposes the
        contact section.  For Instagram the root profile URL is used directly.

        Args:
            social_url: Direct profile URL (must start with ``https://``).
            name: Business name (used only for logging).

        Returns:
            First valid email found on the profile page, or ``None``.
        """
        # Facebook /about reveals the contact section; Instagram root page suffices
        if "facebook.com/" in social_url.lower() and "/about" not in social_url.lower():
            target = social_url.rstrip("/") + "/about"
        else:
            target = social_url

        try:
            html = await self._fetch(target)
            emails = _extract_valid_emails(html)
            if emails:
                logger.info(
                    "[BrightData] Social email for '%s' at %s: %s",
                    name,
                    social_url,
                    emails[0],
                )
                return emails[0]
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "[BrightData] Social profile fetch failed (%s) for '%s': %s",
                social_url,
                name,
                exc,
            )
        return None

    async def _serp_email(
        self,
        name: str,
        phone: Optional[str],
        city: str,
        *,
        social_url: Optional[str] = None,
    ) -> Optional[str]:
        """
        Search Google (via BrightData) for a business email address.

        Priority:
          0. Direct social profile URL (Facebook / Instagram) — fastest, no SERP needed.
          1. ``"{name}" "{formatted_phone}"``  — most precise (guide-artisan.fr, RGE).
          2. ``"{name}" "{city}" email``        — city-scoped search.
          3. ``"{name}" {city} contact email``  — broad fallback (name quoted to avoid pollution).

        Args:
            name: Business name.
            phone: Phone number string (optional, greatly improves P1 accuracy).
            city: City name.
            social_url: Direct Facebook / Instagram profile URL already known
                (e.g. extracted from a PagesJaunes listing).  Tried as P0 before
                falling through to the Google-search tiers.

        Returns:
            First valid email found across all tiers, or ``None``.
        """
        # Priority 0: navigate directly to the social profile — no Google search needed
        if social_url:
            logger.info("[BrightData] SERP email P0 (direct social URL): %s", social_url)
            found = await self._fetch_social_email(social_url, name)
            if found:
                return found

        queries: list[str] = []

        if phone:
            fmt = _normalize_phone(phone)
            queries.append(f'"{name}" "{fmt}"')

        queries.append(f'"{name}" "{city}" email')
        # Keep name quoted in the broad query — prevents cross-business email pollution
        # from directory pages that list multiple local businesses in the same city.
        queries.append(f'"{name}" {city} contact email')

        for query in queries:
            try:
                search_url = (
                    f"https://www.google.com/search"
                    f"?q={quote_plus(query)}&gl=fr&hl=fr&num=10"
                )
                html = await self._fetch(search_url)
                emails = _extract_valid_emails(html)
                if emails:
                    logger.info(
                        "[BrightData] Email for '%s' found via query '%s': %s",
                        name,
                        query,
                        emails[0],
                    )
                    return emails[0]
                await asyncio.sleep(0.3)
            except Exception as exc:  # noqa: BLE001
                logger.debug("[BrightData] SERP email query '%s' failed: %s", query, exc)

        return None

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def scrape(
        self,
        category: str,
        city: str,
        max_results: int = 50,
        *,
        only_without_website: bool = True,
        progress: Optional[ScrapeProgressReporter] = None,
        should_stop: Optional[Callable[[], bool]] = None,
    ) -> List[ProspectCreate]:
        """
        Scrape prospects for *category* + *city* using the BrightData HTTP API.

        Args:
            category: Business category (``"plombier"``, ``"electricien"``, …).
            city: City to search in (French city name, e.g. ``"Bédée"``).
            max_results: Maximum number of prospects to return.
            only_without_website: When ``True``, skip prospects that have a website.
            progress: Optional SSE reporter for streaming progress events.
            should_stop: Optional callable; when it returns ``True`` the scrape
                aborts after the current item.

        Returns:
            List of :class:`ProspectCreate` instances, email-enriched where
            possible, capped at *max_results*.
        """
        logger.info(
            "[BrightData] Starting scrape category=%s city=%s max=%s",
            category,
            city,
            max_results,
        )
        await self.start()

        try:
            # Reload credentials in case they changed since __init__
            self._token = self._load_token()
            self._zone = self._load_zone()

            if not self._token:
                logger.warning(
                    "[BrightData] No API token configured — "
                    "set BRIGHTDATA_API_TOKEN in .env to enable this scraper"
                )
                return []

            if progress:
                await progress.log(
                    f"BrightData — récupération des fiches PagesJaunes ({category} / {city})…"
                )

            # --------------------------------------------------------
            # Phase 1: discover detail pages from the PJ listing
            # --------------------------------------------------------
            fetch_max = max(max_results * 4, 20)
            detail_urls = await self._scrape_pj_listing(category, city, fetch_max)

            if not detail_urls:
                logger.warning(
                    "[BrightData] No detail URLs found for %s / %s", category, city
                )
                if progress:
                    await progress.log("BrightData — aucun résultat trouvé sur PagesJaunes.")
                return []

            if progress:
                await progress.log(
                    f"BrightData — {len(detail_urls)} fiche(s) trouvée(s), analyse en cours…"
                )

            # --------------------------------------------------------
            # Phase 2: scrape detail pages
            # --------------------------------------------------------
            candidates: list[ProspectCreate] = []
            for i, url in enumerate(detail_urls):
                if should_stop and should_stop():
                    break
                if len(candidates) >= max_results:
                    break

                logger.info(
                    "[BrightData] Detail %d/%d: %s",
                    i + 1,
                    min(len(detail_urls), max_results * 4),
                    url,
                )
                prospect = await self._scrape_pj_detail(url, category, city)
                if prospect is None:
                    continue

                if only_without_website and prospect.website:
                    logger.debug("[BrightData] Skipping '%s' (has website)", prospect.name)
                    continue

                candidates.append(prospect)
                await asyncio.sleep(0.3)

            logger.info("[BrightData] %d candidates after website filter", len(candidates))

            if progress:
                await progress.log(
                    f"BrightData — enrichissement des emails ({len(candidates)} prospect(s))…"
                )

            # --------------------------------------------------------
            # Phase 3: email enrichment via Google SERP
            # --------------------------------------------------------
            enriched: list[ProspectCreate] = []
            for prospect in candidates:
                if should_stop and should_stop():
                    break

                if prospect.email:
                    enriched.append(prospect)
                    if progress:
                        await progress.prospect(prospect)
                    continue

                email = await self._serp_email(
                    prospect.name,
                    prospect.phone,
                    prospect.city or city,
                    social_url=prospect.social_url,
                )
                if email:
                    data = prospect.model_dump()
                    data["email"] = email
                    conf = validation_service.calculate_confidence_score(
                        phone=data.get("phone"),
                        address=data.get("address"),
                        email=email,
                        website=data.get("website"),
                    )
                    data["confidence"] = max(1, min(conf, 4))
                    prospect = ProspectCreate(**data)

                enriched.append(prospect)
                if progress:
                    await progress.prospect(prospect)

            logger.info("[BrightData] Final: %d prospects returned", len(enriched))
            return enriched[:max_results]

        except Exception as exc:  # noqa: BLE001
            logger.error("[BrightData] Unexpected error: %s", exc, exc_info=True)
            return []

        finally:
            await self.stop()
