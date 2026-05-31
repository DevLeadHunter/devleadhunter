"""
Yelp scraper for fetching business prospects (nodriver).
"""
from __future__ import annotations

from typing import Callable, List, Optional
from urllib.parse import quote, urljoin, urlparse
import asyncio
import logging
import re

from enums.source import Source
from models.prospect import ProspectCreate
from services.address_service import address_service
from services.validation_service import validation_service
from services.scrape_progress import ScrapeProgressReporter
from scrappers.nodriver_browser import NODRIVER_AVAILABLE, NodriverScraperMixin
from scrappers.nodriver_dom import NodriverDom
from scrappers.nodriver_executor import run_nodriver_task

from .base_scraper import BaseScraper
from .email_scraper import email_scraper

logger = logging.getLogger(__name__)


class YelpScraper(NodriverScraperMixin, BaseScraper):
    """
    Yelp scraper for extracting business prospect data.

    Uses nodriver to interact with Yelp and extract business information.
    Only businesses without websites are targeted.
    """

    def __init__(self) -> None:
        super().__init__(source=Source.YELP)
        self._init_nodriver()
        self.base_url = "https://www.yelp.fr"

    @staticmethod
    def build_url(category: str, city: str) -> str:
        """Build search URL for Yelp France."""
        return (
            f"https://www.yelp.fr/search?find_desc={quote(category)}&find_loc={quote(city)}"
        )

    @staticmethod
    def extract_city(address: str) -> str:
        """Extract city from a Yelp address string."""
        if not address:
            return "Inconnue"
        postal_code_pattern = r"\b(\d{5})\s+(.+)$"
        match = re.search(postal_code_pattern, address)
        if match:
            return match.group(2).strip()
        if "," in address:
            return [p.strip() for p in address.split(",")][-1]
        parts = address.split()
        return parts[-1] if len(parts) >= 2 else "Inconnue"

    async def accept_cookies(self, tab: object) -> None:
        """Accept cookie consent modal if present."""
        selectors = [
            'button[aria-label*="Tout accepter"]',
            "#onetrust-accept-btn-handler",
            ".ot-btn-primary",
        ]
        if await NodriverDom.click_first_matching(tab, selectors):
            logger.info("Yelp cookie consent accepted")
            await asyncio.sleep(0.2)
        elif await NodriverDom.click_by_text(tab, "button", "Accepter"):
            await asyncio.sleep(0.2)

    async def extract_prospect_details(
        self,
        tab: object,
        business_url: str,
        *,
        only_without_website: bool = True,
    ) -> Optional[ProspectCreate]:
        """Extract prospect details from a Yelp business page."""
        try:
            full_url = urljoin(self.base_url, business_url)
            await NodriverDom.navigate(tab, full_url, sleep_s=0.5)
            await self.accept_cookies(tab)

            name = None
            for selector in ('h1[data-font-weight="semibold"]', "h1.css-1se8maq", "h1"):
                name = await NodriverDom.inner_text(tab, selector)
                if name:
                    break
            if not name:
                return None

            category = ""
            for selector in ('a[href*="/c/"]', ".category-str-list a"):
                categories = await NodriverDom.all_inner_texts(tab, selector)
                if categories:
                    category = ", ".join(categories[:2])
                    break
            if not category:
                category = "Inconnu"

            phone = None
            for selector in ('[aria-label*="Téléphone"]', "p.css-1p9ibgf"):
                phone_text = await NodriverDom.inner_text(tab, selector)
                if phone_text:
                    phone_match = re.search(r"[\d\s.\-]+", phone_text)
                    if phone_match:
                        phone = phone_match.group(0).strip()
                        break

            address = None
            for selector in ("address p", '[itemprop="streetAddress"]', "p.css-qyp8bo"):
                address = await NodriverDom.inner_text(tab, selector)
                if address:
                    break

            city = self.extract_city(address) if address else "Inconnue"
            if address:
                address = address_service.remove_city_and_postal_code(address, city)

            website = None
            for selector in ('a[href*="biz_redir"]', "a.css-1um3nx"):
                href = await NodriverDom.get_attribute(tab, selector, "href")
                if href and validation_service.is_valid_website(href):
                    website = href
                    break
            if not website:
                site_link = await NodriverDom.evaluate(
                    tab,
                    """
                    (() => {
                        for (const a of document.querySelectorAll('a')) {
                            const t = (a.innerText || '').toLowerCase();
                            if (t.includes('site web') || t.includes('site')) {
                                return a.getAttribute('href');
                            }
                        }
                        return null;
                    })()
                    """,
                    by_value=True,
                )
                if isinstance(site_link, str) and validation_service.is_valid_website(site_link):
                    website = site_link

            if only_without_website and website:
                logger.info("Prospect %s has a website, skipping", name)
                return None

            email: Optional[str] = None
            try:
                email = await email_scraper.find_email(name, city)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Could not find email: %s", exc)

            confidence = validation_service.calculate_confidence_score(
                phone=phone,
                address=address,
                email=email,
                website=website,
            )

            return ProspectCreate(
                name=name.strip(),
                address=address,
                city=city,
                phone=phone,
                email=email,
                website=website,
                category=category,
                source=Source.YELP,
                confidence=min(confidence, 4),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Error extracting Yelp prospect: %s", exc)
            return None

    @staticmethod
    def _normalize_biz_path(href: str) -> str:
        """Dedupe Yelp business links by path (ignore query string)."""
        parsed = urlparse(href)
        path = parsed.path if parsed.path else href.split("?", 1)[0]
        return path.rstrip("/")

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
        """Scrape prospects from Yelp."""
        if not NODRIVER_AVAILABLE:
            logger.warning("nodriver not available, returning empty results")
            return []

        return await run_nodriver_task(
            lambda: self._scrape_nodriver(
                category, city, max_results, only_without_website, progress, should_stop
            ),
            timeout=600,
        )

    async def _scrape_nodriver(
        self,
        category: str,
        city: str,
        max_results: int,
        only_without_website: bool,
        progress: Optional[ScrapeProgressReporter],
        should_stop: Optional[Callable[[], bool]],
    ) -> List[ProspectCreate]:
        """nodriver bulk scrape for Yelp."""
        logger.info("[Yelp] Starting scrape category=%s city=%s", category, city)
        await self.start()
        try:
            if progress:
                await progress.log("Yelp — chargement de la recherche…")
            tab = await self._nodriver.get_tab()
            url = self.build_url(category, city)
            await NodriverDom.navigate(tab, url, sleep_s=1.0)
            await self.accept_cookies(tab)
            await asyncio.sleep(1.0)

            business_links: list[str] = []
            seen_paths: set[str] = set()
            for selector in ('a[href*="/biz/"]', "h3 a", "a.css-19v1rkv"):
                hrefs = await NodriverDom.evaluate_list(
                    tab,
                    f"""
                    (() => Array.from(document.querySelectorAll({repr(selector)}))
                        .map(a => a.getAttribute('href'))
                        .filter(h => h && h.includes('/biz/')))()
                    """,
                )
                for href in hrefs:
                    if not isinstance(href, str):
                        continue
                    path = self._normalize_biz_path(href)
                    if path in seen_paths:
                        continue
                    seen_paths.add(path)
                    business_links.append(href)
                if business_links:
                    break

            if not business_links:
                logger.info("No results found on Yelp")
                return []

            logger.info("Found %s business links", len(business_links))
            if progress:
                await progress.log(f"Yelp — {len(business_links)} fiche(s) à analyser")
            prospects: list[ProspectCreate] = []

            for link in business_links[: max_results * (10 if only_without_website else 2)]:
                if should_stop and should_stop():
                    break
                if len(prospects) >= max_results:
                    break
                try:
                    prospect = await self.extract_prospect_details(
                        tab,
                        link,
                        only_without_website=only_without_website,
                    )
                    if prospect:
                        prospects.append(prospect)
                        if progress:
                            await progress.prospect(prospect)
                    await asyncio.sleep(0.3)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Error processing Yelp business: %s", exc)

            logger.info("Yelp complete: %s prospects", len(prospects))
            return prospects
        except Exception as exc:  # noqa: BLE001
            logger.error("Error in Yelp scraping: %s", exc, exc_info=True)
            return []
        finally:
            await self.stop()
            await self.close()
