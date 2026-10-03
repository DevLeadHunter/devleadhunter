"""
Email scraper using Google search to find contact emails (nodriver).
"""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import quote_plus

from scrappers.email_candidate_scoring import email_candidate_scorer
from scrappers.nodriver_browser import NODRIVER_AVAILABLE, NodriverBrowser
from scrappers.nodriver_dom import NodriverDom
from scrappers.nodriver_executor import run_nodriver_task
from services.country_profiles import DEFAULT_COUNTRY_CODE, CountryProfiles
from services.sms.phone_normalizer import format_phone_in_national_form

logger = logging.getLogger(__name__)


class EmailScraper:
    """
    Email scraper that searches Google to find business emails.

    Uses nodriver (Chrome CDP) to perform Google searches and extract
    email addresses from result pages.
    """

    def __init__(self) -> None:
        # Ephemeral profile: avoids locking the main scraper's Chrome profile.
        self._browser = NodriverBrowser(ephemeral=True)
        self.email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        # Ranks page emails and rejects town-hall / directory false positives.
        self._scorer = email_candidate_scorer

    @property
    def browser(self) -> object | None:
        """Backward-compatible accessor used by legacy scraper close hooks."""
        return self._browser._browser

    async def ensure_browser(self) -> None:
        """Ensure the nodriver browser is initialized."""
        if not NODRIVER_AVAILABLE:
            logger.warning("nodriver not available, email scraping will be skipped")
            return
        await self._browser.ensure_browser()

    async def close(self) -> None:
        """Close the browser and release resources."""
        await self._browser.close()

    @staticmethod
    def build_google_search_url(query: str, *, country: str = DEFAULT_COUNTRY_CODE, page_number: int = 0) -> str:
        """Google results page of ``query``, ranked for the prospect's country and shown in French.

        Args:
            query: Search query.
            country: ISO code of the prospect's country, sent as ``gl`` (``ch``, ``be``, ``lu``, ``ca``).
            page_number: Zero-based results page.

        Returns:
            The search URL to open.
        """
        region = CountryProfiles.get(country).code.lower()
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&gl={region}&hl=fr"
        if page_number:
            search_url += f"&start={page_number * 10}"
        return search_url

    def extract_emails_from_text(self, text: str) -> list[str]:
        """
        Extract email addresses from text using regex.

        Args:
            text: Text to search for emails.

        Returns:
            List of email addresses found.
        """
        if not text:
            return []
        return self.email_pattern.findall(text)

    async def accept_google_cookies(self, tab: object) -> None:
        """
        Accept Google cookie consent if present.

        Args:
            tab: nodriver Tab instance.
        """
        try:
            await asyncio.sleep(0.5)
            iframe_js = """
            (() => {
                for (const frame of document.querySelectorAll('iframe')) {
                    if ((frame.src || '').includes('consent.google.com')) return true;
                }
                return false;
            })()
            """
            has_consent_frame = await NodriverDom.evaluate(tab, iframe_js, by_value=True)
            if not has_consent_frame:
                return

            clicked = await NodriverDom.click_by_text(tab, "input", "Tout accepter")
            if not clicked:
                clicked = await NodriverDom.click_by_text(tab, "button", "Tout accepter")
            if not clicked:
                clicked = await NodriverDom.click(tab, "input.baseButtonGm3.filledButtonGm3")
            if clicked:
                logger.info("Google cookies accepted")
                await asyncio.sleep(0.5)
        except Exception as exc:
            logger.debug("Could not handle Google cookie consent: %s", exc)

    async def search_google_page(
        self,
        tab: object,
        query: str,
        page_number: int = 0,
        *,
        name: str,
        city: str,
        website: str | None = None,
        country: str = DEFAULT_COUNTRY_CODE,
    ) -> str | None:
        """
        Search Google on a results page and return the email most likely the prospect's.

        Every email on the page is collected, then ``EmailCandidateScorer`` drops
        town-hall / directory false positives and ranks the rest — instead of
        keeping the first address found (which was often the mairie shown on top).

        Args:
            tab: nodriver Tab instance.
            query: Search query.
            page_number: Zero-based page index.
            name: Business name (drives disqualification + ranking).
            city: City name (used by the domain-equals-city reject rule).
            website: Prospect website URL when live — strongest ownership signal.
            country: ISO code of the prospect's country, ranking the results for it.

        Returns:
            Best-scored email found, or None.
        """
        try:
            search_url = self.build_google_search_url(query, country=country, page_number=page_number)
            await NodriverDom.navigate(tab, search_url, sleep_s=0.5)

            if page_number == 0:
                await self.accept_google_cookies(tab)
                await asyncio.sleep(0.5)

            page_text = await tab.get_content()
            email = self._scorer.best_email(page_text, name=name, city=city, website=website)
            if email:
                logger.info(
                    "Best email for query '%s' page %s: %s",
                    query,
                    page_number + 1,
                    email,
                )
            return email
        except Exception as exc:
            logger.debug("Error searching Google page %s for '%s': %s", page_number + 1, query, exc)
            return None

    async def search_google_multiple_pages(
        self,
        tab: object,
        query: str,
        max_pages: int = 3,
        *,
        name: str,
        city: str,
        website: str | None = None,
        country: str = DEFAULT_COUNTRY_CODE,
    ) -> str | None:
        """
        Search Google across multiple pages until a scored email is found.

        Args:
            tab: nodriver Tab instance.
            query: Search query.
            max_pages: Maximum number of result pages to scan.
            name: Business name forwarded to the scorer.
            city: City name forwarded to the scorer.
            website: Prospect website URL when live.
            country: ISO code of the prospect's country, ranking the results for it.

        Returns:
            First page's best email, or None.
        """
        for page_num in range(max_pages):
            email = await self.search_google_page(
                tab, query, page_num, name=name, city=city, website=website, country=country
            )
            if email:
                return email
            if page_num < max_pages - 1:
                await asyncio.sleep(0.5)
        return None

    async def _find_email_nodriver(
        self, name: str, city: str, website: str | None = None, country: str = DEFAULT_COUNTRY_CODE
    ) -> str | None:
        """Internal nodriver implementation for email lookup."""
        if not NODRIVER_AVAILABLE:
            return None

        await self.ensure_browser()
        tab = await self._browser.get_tab()
        try:
            query1 = f"{name} {city} email"
            logger.info("Searching for email with query: %s (3 pages)", query1)
            email = await self.search_google_multiple_pages(
                tab, query1, max_pages=3, name=name, city=city, website=website, country=country
            )
            if email:
                return email

            query2 = f"{name} {city} contact"
            logger.info("Trying contact query: %s (3 pages)", query2)
            return await self.search_google_multiple_pages(
                tab, query2, max_pages=3, name=name, city=city, website=website, country=country
            )
        finally:
            pass

    async def _find_email_smart_nodriver(
        self,
        name: str,
        city: str,
        phone: str | None = None,
        social_url: str | None = None,
        website: str | None = None,
        country: str = DEFAULT_COUNTRY_CODE,
    ) -> str | None:
        """
        Smart email lookup with tiered query strategy (always enabled).

        Priority:
          0. Direct social profile URL from PagesJaunes  — fastest, no Google search needed
          1. ``"{name}" "{phone}"``                       — most targeted (guide-artisan.fr, RGE)
          2. ``"{name}" "{city}" email``                  — city-scoped (page 1 only)
          3. ``"{name}" {city} contact email``            — broad fallback (page 1 only)
          4. Social media bio search (Facebook / Instagram) — last resort (Google → social)

        Args:
            name: Business name.
            city: City name.
            phone: Phone number (optional, greatly improves P1 accuracy), searched the way
                the prospect's country writes it (``079 123 45 67`` for a Swiss business).
            social_url: Direct Facebook / Instagram profile URL already known
                (e.g. extracted from a PagesJaunes listing).  When provided the
                scraper navigates there directly, bypassing the Google SERP step.
            country: ISO code of the prospect's country, ranking every search for it.

        Returns:
            First valid email found, or ``None``.
        """
        if not NODRIVER_AVAILABLE:
            return None

        await self.ensure_browser()
        tab = await self._browser.get_tab()
        try:
            # Priority 0: direct social profile — skip the Google search entirely
            if social_url:
                logger.info("Smart email P0 (direct social URL): %s", social_url)
                found = await self._scrape_social_profile_nodriver(tab, social_url, name, city)
                if found:
                    return found

            # Priority 1: name + phone (most precise)
            if phone:
                phone_formatted = format_phone_in_national_form(phone, country=country) or phone.strip()
                query1 = f'"{name}" "{phone_formatted}"'
                logger.info("Smart email P1 (name+phone): %s", query1)
                email = await self.search_google_multiple_pages(
                    tab, query1, max_pages=2, name=name, city=city, website=website, country=country
                )
                if email:
                    return email

            # Priority 2: name + city + email keyword (page 1 only — page 2 mixes unrelated results)
            query2 = f'"{name}" "{city}" email'
            logger.info("Smart email P2 (name+city): %s", query2)
            email = await self.search_google_multiple_pages(
                tab, query2, max_pages=1, name=name, city=city, website=website, country=country
            )
            if email:
                return email

            # Priority 3: broad fallback — keep name quoted to avoid cross-business pollution
            # (unquoted searches return city-wide listings where a neighbour's email leaks in)
            query3 = f'"{name}" {city} contact email'
            logger.info("Smart email P3 (broad): %s", query3)
            email = await self.search_google_multiple_pages(
                tab, query3, max_pages=1, name=name, city=city, website=website, country=country
            )
            if email:
                return email

            # Priority 4: social media bio search via Google (when no social_url was given)
            # Many small businesses publish their email only in their social profile.
            logger.info("Smart email P4 (social search): %s %s", name, city)
            return await self._find_email_social_nodriver(tab, name, city, phone, country=country)
        finally:
            pass

    async def _scrape_social_profile_nodriver(
        self,
        tab: object,
        social_url: str,
        name: str,
        city: str = "",
    ) -> str | None:
        """
        Navigate directly to a Facebook or Instagram profile and extract an email.

        For Facebook the ``/about`` sub-page is used because it surfaces the
        contact section.  For Instagram the root profile URL is scraped directly.
        The page is passed through the shared scorer so a stray directory address
        embedded in the profile never wins over the business's own contact.

        Args:
            tab: Active nodriver :class:`Tab` instance.
            social_url: Direct profile URL (must contain ``facebook.com/`` or
                ``instagram.com/``).
            name: Business name (drives disqualification + ranking).
            city: City name (used by the domain-equals-city reject rule).

        Returns:
            Best-scored email found on the profile page, or ``None``.
        """
        # Facebook /about exposes the contact section; Instagram root is sufficient
        if "facebook.com/" in social_url.lower() and "/about" not in social_url.lower():
            target = social_url.rstrip("/") + "/about"
        else:
            target = social_url

        try:
            await NodriverDom.navigate(tab, target, sleep_s=1.5)
            page_text = await tab.get_content()
            email = self._scorer.best_email(page_text, name=name, city=city)
            if email:
                logger.info(
                    "Social email for '%s' at %s: %s",
                    name,
                    social_url,
                    email,
                )
                return email
        except Exception as exc:
            logger.debug(
                "Could not scrape social profile %s for '%s': %s",
                social_url,
                name,
                exc,
            )
        return None

    async def _find_email_social_nodriver(
        self,
        tab: object,
        name: str,
        city: str,
        phone: str | None = None,
        *,
        country: str = DEFAULT_COUNTRY_CODE,
    ) -> str | None:
        """
        Search Google for a business social profile and extract an email from it.

        Steps:
        1. Search Google for ``"{name}" "{city}" facebook OR instagram``.
        2. Extract social-profile URLs from the SERP page links via JS.
        3. Delegate each URL to :meth:`_scrape_social_profile_nodriver`.

        Args:
            tab: Active nodriver :class:`Tab` instance.
            name: Business name.
            city: City name.
            phone: Phone number (optional, used to build a tighter query when it is a
                number of the prospect's country, written the way that country writes it).
            country: ISO code of the prospect's country, ranking the search for it.

        Returns:
            Email address extracted from the social profile, or ``None``.
        """
        national_phone = format_phone_in_national_form(phone, country=country) if phone else None
        if national_phone:
            query = f'"{name}" "{national_phone}" facebook OR instagram'
        else:
            query = f'"{name}" "{city}" facebook OR instagram'

        search_url = self.build_google_search_url(query, country=country)
        try:
            await NodriverDom.navigate(tab, search_url, sleep_s=0.5)
        except Exception as exc:
            logger.debug("Social P4 navigate failed: %s", exc)
            return None

        # Collect social-profile URLs from SERP result links (avoid navigation/share URLs).
        # NOTE: evaluate_list() must be used for JS expressions returning arrays —
        # evaluate(..., by_value=True) returns a RemoteObject for array results.
        _js_collect_links = """
        (() => {
            const found = [];
            for (const a of document.querySelectorAll('a[href]')) {
                const h = a.href || '';
                if (
                    (h.includes('facebook.com/') || h.includes('instagram.com/'))
                    && !h.includes('/login')
                    && !h.includes('/signup')
                    && !h.includes('/share')
                    && !h.includes('l.facebook.com')
                    && !h.includes('/search/')
                    && !h.includes('facebook.com/help')
                    && !h.includes('instagram.com/about')
                ) {
                    found.push(h);
                }
            }
            // Unique, prefer page roots over sub-pages
            return [...new Set(found)].slice(0, 5);
        })()
        """
        try:
            # evaluate_list wraps the JS in JSON.stringify so arrays come back as Python lists
            raw_links: list[str] = await NodriverDom.evaluate_list(tab, _js_collect_links)
        except Exception as exc:
            logger.debug("Social P4 link extraction failed: %s", exc)
            return None

        # Keep only genuine profile URLs (path segment of at least 3 non-special chars)
        profile_urls = [link for link in raw_links if re.search(r"(facebook\.com|instagram\.com)/[^/?#]{3,}", link)]

        for profile_url in profile_urls[:2]:
            found = await self._scrape_social_profile_nodriver(tab, profile_url, name, city)
            if found:
                return found

        return None

    async def find_email_smart(
        self,
        name: str,
        city: str,
        phone: str | None = None,
        social_url: str | None = None,
        website: str | None = None,
        *,
        country: str = DEFAULT_COUNTRY_CODE,
    ) -> str | None:
        """
        Find email with smart query prioritisation.

        Unlike ``find_email()``, this method accepts an optional ``social_url``
        (e.g. from PagesJaunes) to bypass the Google search step entirely when a
        direct social profile is known.

        Args:
            name: Business name.
            city: City name.
            phone: Phone number (optional, greatly improves accuracy).
            social_url: Direct Facebook / Instagram profile URL already known.
                When provided, the scraper navigates there first (P0) before
                falling through to the Google-search tiers.
            website: Prospect website URL when live — strongest ownership signal
                for the candidate scorer.
            country: ISO code of the prospect's country: the searches are ranked for it
                and the phone is searched in its national form.

        Returns:
            Email address if found, otherwise None.
        """
        if not NODRIVER_AVAILABLE:
            logger.warning("nodriver not available, skipping smart email search")
            return None

        try:
            return await run_nodriver_task(
                lambda: self._find_email_smart_nodriver(name, city, phone, social_url, website, country),
                timeout=120,
            )
        except Exception as exc:
            logger.error("Error in smart email scraper: %s", exc)
            return None

    async def find_email(
        self, name: str, city: str, website: str | None = None, *, country: str = DEFAULT_COUNTRY_CODE
    ) -> str | None:
        """
        Find an email address for a business via Google search.

        Always attempts the lookup when a browser engine is available — we
        recover the contact email whenever it is publicly discoverable.

        Args:
            name: Business name.
            city: City name.
            website: Prospect website URL when live — strongest ownership signal
                for the candidate scorer.
            country: ISO code of the prospect's country, ranking the searches for it.
        """
        if not NODRIVER_AVAILABLE:
            logger.warning("nodriver not available, skipping email search")
            return None

        try:
            return await run_nodriver_task(
                lambda: self._find_email_nodriver(name, city, website, country),
                timeout=120,
            )
        except Exception as exc:
            logger.error("Error in email scraper: %s", exc)
            return None


email_scraper = EmailScraper()
