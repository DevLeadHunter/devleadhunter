"""
Pages Jaunes scraper for fetching business prospects (nodriver).
"""
from __future__ import annotations

from typing import Callable, List, Optional
from urllib.parse import urljoin
import asyncio
import base64
import json
import logging
import re

from enums.source import Source
from models.prospect import ProspectCreate
from services.address_service import address_service
from services.validation_service import validation_service
from services.scrape_progress import ScrapeProgressReporter
from scrappers.nodriver_browser import NODRIVER_AVAILABLE, NodriverScraperMixin, resolve_scraper_headless
from scrappers.nodriver_dom import NodriverDom
from scrappers.nodriver_executor import run_nodriver_task

from .base_scraper import BaseScraper
from .email_scraper import email_scraper

logger = logging.getLogger(__name__)


class PagesJaunesScraper(NodriverScraperMixin, BaseScraper):
    """
    Pages Jaunes scraper for extracting business prospect data.

    Uses nodriver to interact with Pages Jaunes and extract business
    information. Only businesses without websites are targeted.
    """

    def __init__(self) -> None:
        super().__init__(source=Source.PAGESJAUNES)
        self._init_nodriver()
        self.base_url = "https://www.pagesjaunes.fr"

    @staticmethod
    def build_url(category: str, city: str) -> str:
        """Build search URL for Pages Jaunes."""
        category_map = {
            "plombier": "plombiers",
            "restaurant": "restaurants",
            "coiffeur": "coiffeurs",
            "electricien": "electriciens",
            "garage": "garages-auto",
        }
        search_category = category_map.get(category.lower().strip(), category.lower().strip())
        city_slug = city.lower().strip().replace(" ", "-")
        return f"https://www.pagesjaunes.fr/annuaire/{city_slug}/{search_category}"

    @staticmethod
    def extract_city(address: str) -> str:
        """Extract city from a Pages Jaunes address string."""
        if not address:
            return "Inconnue"
        postal_code_pattern = r"\b(\d{5})\s+(.+)$"
        match = re.search(postal_code_pattern, address)
        if match:
            return match.group(2).strip()
        parts = address.split()
        if len(parts) >= 2:
            return parts[-1]
        return "Inconnue"

    async def accept_cookies(self, tab: object) -> None:
        """
        Accept cookie consent modal if present.

        Args:
            tab: nodriver Tab instance.
        """
        try:
            if await NodriverDom.query_count(tab, "#appconsent") == 0:
                return

            logger.info("Cookie consent modal detected — accept manually if auto-click fails")
            await asyncio.sleep(0.5)

            # nodriver can click inside the consent iframe via CDP select
            for selector in (
                "button.button__acceptAll",
                'button[class*="button__acceptAll"]',
                ".button__acceptAll",
            ):
                try:
                    btn = await tab.select(f"#appconsent iframe >>> {selector}", timeout=3)
                    if btn:
                        await btn.click()
                        logger.info("Cookie consent accepted (iframe select)")
                        await asyncio.sleep(0.3)
                        return
                except Exception:  # noqa: BLE001
                    continue

            iframe_js = """
            (() => {
                const iframe = document.querySelector('#appconsent iframe');
                if (!iframe || !iframe.contentDocument) return false;
                const selectors = [
                    'button[class*="button__acceptAll"]',
                    'button.button__acceptAll',
                    '.button__acceptAll',
                ];
                for (const sel of selectors) {
                    const btn = iframe.contentDocument.querySelector(sel);
                    if (btn) { btn.click(); return true; }
                }
                for (const btn of iframe.contentDocument.querySelectorAll('button')) {
                    const t = (btn.innerText || btn.textContent || '').toLowerCase();
                    if (t.includes('accepter')) { btn.click(); return true; }
                }
                return false;
            })()
            """
            if await NodriverDom.evaluate(tab, iframe_js, by_value=True):
                logger.info("Cookie consent accepted in iframe")
                await asyncio.sleep(0.1)
                return

            selectors = [
                'button[class*="button__acceptAll"]',
                "button.button__acceptAll",
                ".button__acceptAll",
            ]
            if await NodriverDom.click_first_matching(tab, selectors):
                logger.info("Cookie consent accepted")
                await asyncio.sleep(0.1)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not handle cookie consent: %s", exc)

    async def _wait_for_results(self, tab: object, *, timeout_s: float = 20.0) -> int:
        """Wait until result cards appear and return the card count."""
        deadline = asyncio.get_running_loop().time() + timeout_s
        while asyncio.get_running_loop().time() < deadline:
            await self.accept_cookies(tab)
            count = await NodriverDom.query_count(tab, "section.results#listResults li.bi")
            if count == 0:
                count = await NodriverDom.query_count(tab, "li.bi")
            if count > 0:
                return count
            await NodriverDom.scroll_element(tab, "section.results#listResults", 400)
            await asyncio.sleep(0.4)
        return 0

    async def _collect_card_hrefs(self, tab: object) -> list[str]:
        """Extract detail-page links from the current results list."""
        return await NodriverDom.evaluate_list(
            tab,
            """
            (() => {
                const out = [];
                const cards = document.querySelectorAll(
                    'section.results#listResults li.bi, ul.list-results li.bi, li.bi'
                );
                for (const card of cards) {
                    const link = card.querySelector('a.bi-denomination, a[href*="/pros/"], a[href*="/annuaire/"]');
                    if (!link) continue;
                    let href = link.getAttribute('href');
                    if (href && href !== '#') {
                        out.push(href);
                        continue;
                    }
                    const raw = link.getAttribute('data-pjlb');
                    if (!raw || !raw.includes('url')) continue;
                    try {
                        const data = JSON.parse(raw.replace(/&quot;/g, '"'));
                        const decoded = atob(data.url);
                        out.push(decoded.replace(/^\\//, ''));
                    } catch (e) {}
                }
                return out;
            })()
            """,
        )

    async def extract_prospect_details(
        self,
        tab: object,
        link_url: str,
        *,
        search_city: str,
        only_without_website: bool = True,
    ) -> Optional[ProspectCreate]:
        """
        Extract prospect details from a detail page.

        Args:
            tab: nodriver Tab instance (reused).
            link_url: Relative or absolute URL to the detail page.
            search_city: City from the search query (fallback).

        Returns:
            ProspectCreate or None if extraction fails or prospect has a website.
        """
        try:
            full_url = urljoin(self.base_url, link_url)
            await NodriverDom.navigate(tab, full_url, sleep_s=0.5)
            await self.accept_cookies(tab)

            name_html = await NodriverDom.inner_html(tab, "#teaser-header h1.noTrad.no-margin")
            if not name_html:
                logger.warning("Name not found on detail page")
                return None

            match = re.search(r"^([^<\n]+)", name_html)
            if match:
                name = match.group(1).strip()
            else:
                full_text = await NodriverDom.inner_text(tab, "#teaser-header h1.noTrad.no-margin")
                name = (full_text or "").split("\n")[0].strip()
            if not name:
                return None

            categories = await NodriverDom.all_inner_texts(tab, ".zone-activites .activite")
            category = ", ".join(categories[:2]) if categories else "Inconnu"

            phone = None
            for phone_selector in (
                "span.coord-numero.noTrad",
                "span.coord-numero",
                ".num-container span.coord-numero",
                "#coord-liste-numero_1 span.coord-numero",
            ):
                count = await NodriverDom.query_count(tab, phone_selector)
                for i in range(count):
                    phone_text = await NodriverDom.inner_text(tab, phone_selector, index=i)
                    if phone_text and any(c.isdigit() for c in phone_text) and len(phone_text) >= 8:
                        phone = re.sub(r"\s+", " ", phone_text).strip()
                        break
                if phone:
                    break

            address = None
            for selector in (
                "a.black-icon.teaser-item span.noTrad",
                ".address.streetAddress",
                "#blocCoordonnees a.black-icon span.noTrad",
                'a[title*="carte"] span.noTrad',
            ):
                address = await NodriverDom.inner_text(tab, selector)
                if address:
                    break

            city = self.extract_city(address) if address else search_city
            if address:
                address = address_service.remove_city_and_postal_code(address, city)

            website = None
            for selector in (".MINISITE.pj-link", ".SITE_EXTERNE.pj-link"):
                href = await NodriverDom.get_attribute(tab, selector, "href")
                if not href or href == "#" or not href.startswith("http"):
                    data_pjlb = await NodriverDom.get_attribute(tab, selector, "data-pjlb")
                    if data_pjlb:
                        try:
                            data = json.loads(data_pjlb.replace("&quot;", '"'))
                            encoded_url = data.get("url", "")
                            href = base64.b64decode(encoded_url).decode("utf-8")
                        except Exception as exc:  # noqa: BLE001
                            logger.debug("Could not decode data-pjlb: %s", exc)
                if href and validation_service.is_valid_website(href):
                    website = href
                    break

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
                source=Source.PAGESJAUNES,
                confidence=min(confidence, 4),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Error extracting prospect details: %s", exc)
            return None

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
        Scrape prospects from Pages Jaunes.

        Args:
            category: Business category to search for.
            city: City to search in.
            max_results: Maximum number of results to return.

        Returns:
            List of prospects without websites.
        """
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
        """nodriver bulk scrape for Pages Jaunes."""
        logger.info(
            "[PagesJaunes] Starting scrape category=%s city=%s max=%s",
            category,
            city,
            max_results,
        )
        await self.start()
        try:
            if progress:
                await progress.log("Pages Jaunes — chargement de la recherche…")
            tab = await self._nodriver.get_tab()
            url = self.build_url(category, city)
            logger.info("[PagesJaunes] Navigating to %s", url)
            await NodriverDom.navigate(tab, url, sleep_s=1.2 if not resolve_scraper_headless() else 0.8)
            await self.accept_cookies(tab)

            if await NodriverDom.query_count(tab, "h1.wording-no-responses") > 0:
                logger.info("No results found on Pages Jaunes")
                return []

            card_count = await self._wait_for_results(tab, timeout_s=25.0)
            if card_count == 0:
                logger.warning(
                    "Results section not found on Pages Jaunes (url=%s)",
                    NodriverDom.tab_url(tab),
                )
                return []

            logger.info("Found %s prospect cards on list page", card_count)

            for _ in range(3):
                await NodriverDom.scroll_element(tab, "section.results#listResults", 800)
                await asyncio.sleep(0.35)

            card_hrefs: list[str] = await self._collect_card_hrefs(tab)
            logger.info("Collected %s detail links", len(card_hrefs))
            if progress:
                await progress.log(f"Pages Jaunes — {len(card_hrefs)} fiche(s) à analyser")

            if not card_hrefs:
                logger.warning("No detail links extracted — DOM may have changed")
                return []

            prospects: list[ProspectCreate] = []
            processed = 0
            max_to_check = min(
                max(max_results * (10 if only_without_website else 2), 10),
                len(card_hrefs),
            )

            for i in range(max_to_check):
                if should_stop and should_stop():
                    break
                if len(prospects) >= max_results:
                    break

                try:
                    href = card_hrefs[i]
                    if not href:
                        continue

                    logger.info("[PagesJaunes] Opening detail %s/%s: %s", i + 1, max_to_check, href)
                    prospect = await self.extract_prospect_details(
                        tab,
                        href,
                        search_city=city,
                        only_without_website=only_without_website,
                    )
                    if prospect:
                        prospects.append(prospect)
                        if progress:
                            await progress.prospect(prospect)
                    processed += 1
                    await asyncio.sleep(0.2)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Error processing card %s: %s", i, exc)

            logger.info(
                "Pages Jaunes complete: %s prospects from %s processed",
                len(prospects),
                processed,
            )
            return prospects
        except Exception as exc:  # noqa: BLE001
            logger.error("Error in Pages Jaunes scraping: %s", exc, exc_info=True)
            return []
        finally:
            await self.stop()
            await self.close()
