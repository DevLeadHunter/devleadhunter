"""
Pages Jaunes scraper for fetching business prospects.

Scraping cascade (fastest → safest):
  1. Pure HTTP  — aiohttp + BeautifulSoup, no Chrome at all.
  2. Headless   — nodriver Chrome without a visible window.
  3. Visible    — nodriver Chrome with a visible window (current fallback).

Each tier is tried in order; the first one that returns results is used.
A tier is skipped when Pages Jaunes clearly blocks it (bot-detection, missing
DOM structure that requires JS, etc.).
"""
from __future__ import annotations

from typing import Callable, List, Optional
from urllib.parse import urljoin
import asyncio
import base64
import json
import logging
import re

import aiohttp
from bs4 import BeautifulSoup

from enums.source import Source
from models.prospect import ProspectCreate
from services.address_service import address_service
from services.validation_service import validation_service
from services.scrape_progress import ScrapeProgressReporter
from scrappers.nodriver_browser import NODRIVER_AVAILABLE, NodriverBrowser, NodriverScraperMixin, resolve_scraper_headless
from scrappers.nodriver_dom import NodriverDom
from scrappers.nodriver_executor import run_nodriver_task

from .base_scraper import BaseScraper
from .email_scraper import email_scraper

logger = logging.getLogger(__name__)

# ─── HTTP request headers ─────────────────────────────────────────────────────

_HTTP_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}


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

            website: Optional[str] = None
            # Transient: Facebook / Instagram URL found on the PJ profile.
            # Many businesses list their FB/IG page instead of a real website.
            # We never store this in the DB but carry it through email enrichment.
            social_url: Optional[str] = None
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
                if not href:
                    continue
                if validation_service.is_valid_website(href):
                    website = href
                    break
                # Not a valid business website — detect social profile URLs so we
                # can skip the Google search for the Facebook/Instagram page later.
                href_low = href.lower()
                if social_url is None and (
                    "facebook.com/" in href_low or "instagram.com/" in href_low
                ):
                    social_url = href
                    logger.debug("[PJ] Social URL captured for '%s': %s", name, href)

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
                social_url=social_url,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Error extracting prospect details: %s", exc)
            return None

    # ─── HTTP cascade tier 1 ─────────────────────────────────────────────────

    @staticmethod
    def _pj_is_blocked(html: str) -> bool:
        """
        Detect Pages Jaunes bot-blocking in a raw HTML response.

        Returns True when the HTML looks like a captcha / challenge page or
        when the main listing structure is entirely absent (JS-only render).
        """
        low = html.lower()
        blocking_markers = (
            "cf-turnstile",
            "g-recaptcha",
            "captcha",
            "access denied",
            "403 forbidden",
            "challenge-platform",
            "bot detection",
            "veuillez patienter",   # Cloudflare "please wait"
            "ddos-guard",
        )
        if any(m in low for m in blocking_markers):
            return True
        # Listing page: PagesJaunes renders cards server-side for SEO, but when
        # bot-detection kicks in the HTML ships without ANY li.bi elements AND
        # without the "no results" heading.  Both missing → treat as blocked.
        has_cards = "bi-denomination" in html or 'class="bi ' in html or "li.bi" in html
        has_no_results = "wording-no-responses" in html or "noResponseTitle" in html
        return not has_cards and not has_no_results

    async def _http_fetch(
        self,
        url: str,
        *,
        session: aiohttp.ClientSession,
    ) -> Optional[str]:
        """
        GET *url* with browser-like headers.

        Returns the HTML string on success, or None when the server returns
        a non-2xx status code or when the response looks like a bot-block.
        """
        try:
            async with session.get(
                url,
                headers=_HTTP_HEADERS,
                timeout=aiohttp.ClientTimeout(total=30),
                allow_redirects=True,
            ) as resp:
                if resp.status >= 400:
                    logger.info("[PJ-HTTP] Blocked — status %s for %s", resp.status, url)
                    return None
                html = await resp.text()
                return html
        except Exception as exc:  # noqa: BLE001
            logger.info("[PJ-HTTP] Request failed for %s: %s", url, exc)
            return None

    def _http_parse_listing(self, html: str) -> Optional[list[str]]:
        """
        Parse a Pages Jaunes listing page and extract detail-page hrefs.

        Returns:
            None  — page looks bot-blocked (no recognisable structure).
            []    — page loaded fine but contains zero results.
            [..] — list of relative or absolute detail-page URLs.
        """
        if self._pj_is_blocked(html):
            logger.info("[PJ-HTTP] Listing page blocked or empty (captcha / JS-gate)")
            return None

        soup = BeautifulSoup(html, "html.parser")

        # "No results" heading — legitimate empty search
        if soup.select_one("h1.wording-no-responses") or soup.select_one(".noResponseTitle"):
            logger.info("[PJ-HTTP] No results for this search (legitimate empty page)")
            return []

        seen: set[str] = set()
        urls: list[str] = []

        # Method 1: direct href on business-card anchor tags
        for a_tag in soup.find_all("a", href=True):
            href: str = a_tag["href"]
            clean = href.split("?")[0]
            if re.search(r"/pros/\d+$", clean) and clean not in seen:
                seen.add(clean)
                urls.append(clean)

        # Method 2: base64-encoded links in data-pjlb attributes
        for a_tag in soup.find_all("a", attrs={"data-pjlb": True}):
            raw_attr: str = a_tag["data-pjlb"].replace("&quot;", '"')
            try:
                data = json.loads(raw_attr)
                encoded_url: str = data.get("url", "")
                decoded = base64.b64decode(encoded_url).decode("utf-8").lstrip("/")
                if "pros/" in decoded:
                    full = urljoin(self.base_url + "/", decoded)
                    clean = full.split("?")[0]
                    if clean not in seen:
                        seen.add(clean)
                        urls.append(clean)
            except Exception:  # noqa: BLE001
                continue

        if not urls:
            # Got a valid page but couldn't extract any card links — likely
            # the page is JS-rendered (cards are injected client-side).
            logger.info("[PJ-HTTP] Listing page loaded but no card links found — JS-rendered?")
            return None

        logger.info("[PJ-HTTP] Extracted %d detail URLs from listing page", len(urls))
        return urls

    def _http_parse_detail(
        self,
        html: str,
        *,
        search_city: str,
        only_without_website: bool,
    ) -> Optional[ProspectCreate]:
        """
        Parse a Pages Jaunes business detail page fetched via plain HTTP.

        Returns a ProspectCreate on success, or None when the page couldn't
        be parsed (missing name, or prospect has website when only_without_website=True).
        """
        soup = BeautifulSoup(html, "html.parser")

        # -- Name --
        name = ""
        for sel in ("#teaser-header h1.noTrad.no-margin", "h1.noTrad", "h1.denomination", "h1"):
            el = soup.select_one(sel)
            if el:
                # Take only the direct text node — ignore child spans (ratings, etc.)
                direct = el.find(string=True, recursive=False)
                name = (direct or el.get_text(" ", strip=True)).strip().split("\n")[0].strip()
                if name:
                    break
        if not name:
            return None

        # -- Category --
        cats = [el.get_text(strip=True) for el in soup.select(".zone-activites .activite")]
        category = ", ".join(cats[:2]) if cats else "Inconnu"

        # -- Phone --
        phone: Optional[str] = None
        for sel in ("span.coord-numero.noTrad", "span.coord-numero", ".num-container span"):
            el = soup.select_one(sel)
            if el:
                candidate = el.get_text(strip=True)
                if re.search(r"\d{8,}", re.sub(r"\s", "", candidate)):
                    phone = re.sub(r"\s+", " ", candidate).strip()
                    break
        if not phone:
            for a_tag in soup.find_all("a", href=re.compile(r"^tel:")):
                digits = re.sub(r"\D", "", a_tag["href"])
                if len(digits) >= 9:
                    phone = digits
                    break

        # -- Address --
        address: Optional[str] = None
        for sel in (
            "a.black-icon.teaser-item span.noTrad",
            ".address.streetAddress",
            "#blocCoordonnees a.black-icon span.noTrad",
            'a[title*="carte"] span.noTrad',
            "span.address",
        ):
            el = soup.select_one(sel)
            if el:
                address = el.get_text(" ", strip=True)
                break

        # -- City --
        city = self.extract_city(address) if address else search_city
        if address:
            address = address_service.remove_city_and_postal_code(address, city)

        # -- Website & social URL --
        website: Optional[str] = None
        social_url: Optional[str] = None
        for sel in (".MINISITE.pj-link", ".SITE_EXTERNE.pj-link", "a.MINISITE", "a.SITE_EXTERNE"):
            el = soup.select_one(sel)
            if not el:
                continue
            href = el.get("href", "") or ""
            if not href or href == "#":
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
            if validation_service.is_valid_website(href):
                website = href
                break
            href_low = href.lower()
            if social_url is None and (
                "facebook.com/" in href_low or "instagram.com/" in href_low
            ):
                social_url = href
                logger.debug("[PJ-HTTP] Social URL for '%s': %s", name, href)

        if only_without_website and website:
            logger.info("[PJ-HTTP] Skipping %s — has website", name)
            return None

        confidence = validation_service.calculate_confidence_score(
            phone=phone,
            address=address,
            email=None,
            website=website,
        )

        return ProspectCreate(
            name=name.strip(),
            address=address,
            city=city,
            phone=phone,
            email=None,           # email enrichment happens in auto_scraper
            website=website,
            category=category,
            source=Source.PAGESJAUNES,
            confidence=min(confidence, 4),
            social_url=social_url,
        )

    async def _try_http(
        self,
        category: str,
        city: str,
        max_results: int,
        only_without_website: bool,
        progress: Optional[ScrapeProgressReporter],
        should_stop: Optional[Callable[[], bool]],
    ) -> Optional[List[ProspectCreate]]:
        """
        Tier-1: attempt a pure HTTP scrape of Pages Jaunes (no Chrome).

        Returns:
            None  — PagesJaunes blocked plain HTTP (move on to next tier).
            list  — scraped prospects (may be empty if the search has no results).
        """
        logger.info("[PJ-HTTP] Trying pure-HTTP tier for category=%s city=%s", category, city)
        if progress:
            await progress.log("Pages Jaunes — tentative HTTP (sans Chrome)…")

        url = self.build_url(category, city)
        async with aiohttp.ClientSession() as session:
            # 1. Fetch and parse the listing page
            html = await self._http_fetch(url, session=session)
            if html is None:
                logger.info("[PJ-HTTP] Listing fetch returned no HTML — falling through")
                return None

            detail_hrefs = self._http_parse_listing(html)
            if detail_hrefs is None:
                logger.info("[PJ-HTTP] Listing parse returned None (blocked/JS) — falling through")
                return None
            if not detail_hrefs:
                logger.info("[PJ-HTTP] No results found via HTTP")
                return []

            if progress:
                await progress.log(f"Pages Jaunes HTTP — {len(detail_hrefs)} fiche(s) à analyser")

            # 2. Fetch and parse each detail page
            prospects: list[ProspectCreate] = []
            max_to_check = min(
                max(max_results * (10 if only_without_website else 2), 10),
                len(detail_hrefs),
            )

            for i, href in enumerate(detail_hrefs[:max_to_check]):
                if should_stop and should_stop():
                    break
                if len(prospects) >= max_results:
                    break

                full_url = href if href.startswith("http") else urljoin(self.base_url, href)
                logger.info("[PJ-HTTP] Detail %d/%d: %s", i + 1, max_to_check, full_url)

                detail_html = await self._http_fetch(full_url, session=session)
                if detail_html is None:
                    # Single detail page blocked — skip, don't abort the whole run
                    logger.debug("[PJ-HTTP] Detail %s fetch blocked, skipping", full_url)
                    continue

                prospect = self._http_parse_detail(
                    detail_html,
                    search_city=city,
                    only_without_website=only_without_website,
                )
                if prospect:
                    prospects.append(prospect)
                    if progress:
                        await progress.prospect(prospect)

                # Small courtesy delay to avoid hammering PJ
                await asyncio.sleep(0.3)

        logger.info("[PJ-HTTP] HTTP tier complete: %d prospects", len(prospects))
        return prospects

    # ─── Nodriver cascade tier 2 (headless) ──────────────────────────────────

    async def _try_nodriver_headless(
        self,
        category: str,
        city: str,
        max_results: int,
        only_without_website: bool,
        progress: Optional[ScrapeProgressReporter],
        should_stop: Optional[Callable[[], bool]],
    ) -> Optional[List[ProspectCreate]]:
        """
        Tier-2: attempt a headless-Chrome scrape of Pages Jaunes.

        Temporarily replaces ``self._nodriver`` with a headless browser for
        the duration of this attempt, then restores the original instance
        regardless of outcome.

        Returns:
            None  — Chrome failed to start / navigate (move on to tier-3).
            list  — scraped prospects (may be empty).
        """
        logger.info("[PJ-headless] Trying headless-Chrome tier")
        if progress:
            await progress.log("Pages Jaunes — tentative headless Chrome…")

        original_nodriver = self._nodriver
        self._nodriver = NodriverBrowser(headless=True)
        try:
            result = await self._scrape_nodriver(
                category, city, max_results, only_without_website, progress, should_stop
            )
            # If headless Chrome returned zero results we cannot tell whether
            # the search is genuinely empty or PagesJaunes blocked the headless
            # browser (captcha / challenge page).  Return None so visible Chrome
            # can confirm — it will also return [] quickly if the search is truly
            # empty (the "no results" heading appears immediately in visible mode).
            if not result:
                logger.info(
                    "[PJ-headless] 0 results — could be blocked, falling through to visible Chrome"
                )
                return None
            return result
        except Exception as exc:  # noqa: BLE001
            logger.warning("[PJ-headless] Headless Chrome tier failed: %s", exc)
            return None
        finally:
            # _scrape_nodriver already called close() — make sure and restore
            try:
                await self._nodriver.close()
            except Exception:  # noqa: BLE001
                pass
            self._nodriver = original_nodriver

    # ─── Public entry point ───────────────────────────────────────────────────

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
        Scrape prospects from Pages Jaunes using a three-tier cascade:

        1. Pure HTTP (aiohttp + BeautifulSoup) — fastest, no Chrome.
        2. Headless Chrome (nodriver, no visible window).
        3. Visible Chrome (nodriver, current fallback).

        Args:
            category: Business category to search for.
            city: City to search in.
            max_results: Maximum number of results to return.

        Returns:
            List of prospects (empty list if the search has no results or all
            tiers are blocked).
        """
        # ── Tier 1: pure HTTP ─────────────────────────────────────────────────
        http_result = await self._try_http(
            category, city, max_results, only_without_website, progress, should_stop
        )
        if http_result is not None:
            logger.info("[PJ] HTTP tier succeeded — skipping Chrome")
            return http_result

        # ── Tier 2: headless Chrome ───────────────────────────────────────────
        if not NODRIVER_AVAILABLE:
            logger.warning("[PJ] nodriver not available — only HTTP was attempted")
            return []

        logger.info("[PJ] HTTP tier blocked — trying headless Chrome")
        headless_result = await run_nodriver_task(
            lambda: self._try_nodriver_headless(
                category, city, max_results, only_without_website, progress, should_stop
            ),
            timeout=600,
        )
        if headless_result is not None:
            logger.info("[PJ] Headless Chrome tier succeeded")
            return headless_result

        # ── Tier 3: visible Chrome (original behaviour) ───────────────────────
        logger.info("[PJ] Headless Chrome tier blocked — falling back to visible Chrome")
        if progress:
            await progress.log("Pages Jaunes — fallback Chrome visible…")
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
