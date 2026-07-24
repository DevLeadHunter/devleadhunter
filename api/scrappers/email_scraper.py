"""
Email scraper using Google search to find contact emails (nodriver).
"""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import quote_plus

from scrappers.nodriver_browser import NODRIVER_AVAILABLE, NodriverBrowser
from scrappers.nodriver_dom import NodriverDom
from scrappers.nodriver_executor import run_nodriver_task

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

    async def search_google_page(self, tab: object, query: str, page_number: int = 0) -> str | None:
        """
        Search Google on a specific results page and extract the first valid email.

        Args:
            tab: nodriver Tab instance.
            query: Search query.
            page_number: Zero-based page index.

        Returns:
            First valid email found, or None.
        """
        try:
            if page_number == 0:
                search_url = f"https://www.google.com/search?q={quote_plus(query)}"
            else:
                start_param = page_number * 10
                search_url = f"https://www.google.com/search?q={quote_plus(query)}&start={start_param}"

            await NodriverDom.navigate(tab, search_url, sleep_s=0.5)

            if page_number == 0:
                await self.accept_google_cookies(tab)
                await asyncio.sleep(0.5)

            page_text = await tab.get_content()
            emails = self.extract_emails_from_text(page_text)

            if emails:
                spam_domains = [
                    # Generic / placeholder
                    "example.com",
                    "test.com",
                    "domain.com",
                    "yoursite.com",
                    # Big platforms
                    "google.com",
                    "gstatic.com",
                    "facebook.com",
                    "instagram.com",
                    "twitter.com",
                    "linkedin.com",
                    "youtube.com",
                    "tiktok.com",
                    # Review / aggregator sites
                    "eldo.com",
                    "avis-verifies.com",
                    "trustpilot.com",
                    "tripadvisor.com",
                    "tripadvisor.fr",
                    "yelp.com",
                    "yelp.fr",
                    # Generic artisan / professional directories
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
                    # Genealogy / off-topic sites that appear in broad searches
                    "geneafrance.com",
                    "geneanet.org",
                    "filae.com",
                ]
                # Reject HTML-encoding artifacts (e.g. "u003e" = ">") and
                # generic role addresses from directories that are never the
                # actual business contact
                spam_prefixes = (
                    "u003",
                    "u0022",  # HTML entity remnants
                    "noreply",
                    "no-reply",
                    "donotreply",
                    "service-avis",
                    "avis@",
                    "mairie",  # city-hall addresses (mairie@ville.fr etc.)
                )

                def _is_valid(addr: str) -> bool:
                    low = addr.lower()
                    if any(sp in low for sp in spam_domains):
                        return False
                    local = low.split("@")[0]
                    return not any(local.startswith(pfx) for pfx in spam_prefixes)

                filtered = [e for e in emails if _is_valid(e)]
                if filtered:
                    logger.info(
                        "Found email(s) for query '%s' page %s: %s",
                        query,
                        page_number + 1,
                        filtered,
                    )
                    return filtered[0]
            return None
        except Exception as exc:
            logger.debug("Error searching Google page %s for '%s': %s", page_number + 1, query, exc)
            return None

    async def search_google_multiple_pages(self, tab: object, query: str, max_pages: int = 3) -> str | None:
        """
        Search Google across multiple pages until an email is found.

        Args:
            tab: nodriver Tab instance.
            query: Search query.
            max_pages: Maximum number of result pages to scan.

        Returns:
            First email found, or None.
        """
        for page_num in range(max_pages):
            email = await self.search_google_page(tab, query, page_num)
            if email:
                return email
            if page_num < max_pages - 1:
                await asyncio.sleep(0.5)
        return None

    async def _find_email_nodriver(self, name: str, city: str) -> str | None:
        """Internal nodriver implementation for email lookup."""
        if not NODRIVER_AVAILABLE:
            return None

        await self.ensure_browser()
        tab = await self._browser.get_tab()
        try:
            query1 = f"{name} {city} email"
            logger.info("Searching for email with query: %s (3 pages)", query1)
            email = await self.search_google_multiple_pages(tab, query1, max_pages=3)
            if email:
                return email

            query2 = f"{name} {city} contact"
            logger.info("Trying contact query: %s (3 pages)", query2)
            return await self.search_google_multiple_pages(tab, query2, max_pages=3)
        finally:
            pass

    async def _find_email_smart_nodriver(
        self,
        name: str,
        city: str,
        phone: str | None = None,
        social_url: str | None = None,
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
            phone: Phone number (optional, greatly improves P1 accuracy).
            social_url: Direct Facebook / Instagram profile URL already known
                (e.g. extracted from a PagesJaunes listing).  When provided the
                scraper navigates there directly, bypassing the Google SERP step.

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
                found = await self._scrape_social_profile_nodriver(tab, social_url, name)
                if found:
                    return found

            # Priority 1: name + phone (most precise)
            if phone:
                phone_clean = re.sub(r"[\-\.\(\)]", "", phone).strip()
                # Ensure spaces in French format: "06 63 96 82 57"
                digits_only = re.sub(r"\s+", "", phone_clean)
                if digits_only.startswith("33") and len(digits_only) == 11:
                    # International +33… → 0…
                    digits_only = "0" + digits_only[2:]
                if len(digits_only) == 10:
                    phone_formatted = " ".join(digits_only[i : i + 2] for i in range(0, 10, 2))
                else:
                    phone_formatted = phone.strip()
                query1 = f'"{name}" "{phone_formatted}"'
                logger.info("Smart email P1 (name+phone): %s", query1)
                email = await self.search_google_multiple_pages(tab, query1, max_pages=2)
                if email:
                    return email

            # Priority 2: name + city + email keyword (page 1 only — page 2 mixes unrelated results)
            query2 = f'"{name}" "{city}" email'
            logger.info("Smart email P2 (name+city): %s", query2)
            email = await self.search_google_multiple_pages(tab, query2, max_pages=1)
            if email:
                return email

            # Priority 3: broad fallback — keep name quoted to avoid cross-business pollution
            # (unquoted searches return city-wide listings where a neighbour's email leaks in)
            query3 = f'"{name}" {city} contact email'
            logger.info("Smart email P3 (broad): %s", query3)
            email = await self.search_google_multiple_pages(tab, query3, max_pages=1)
            if email:
                return email

            # Priority 4: social media bio search via Google (when no social_url was given)
            # Many small businesses publish their email only in their social profile.
            logger.info("Smart email P4 (social search): %s %s", name, city)
            return await self._find_email_social_nodriver(tab, name, city, phone)
        finally:
            pass

    # Spam domains that are never a real business contact email
    _SOCIAL_SPAM_DOMAINS: tuple[str, ...] = (
        "example.com",
        "test.com",
        "google.com",
        "gstatic.com",
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "linkedin.com",
        "pagesjaunes.fr",
        "yelp.com",
        "tripadvisor.com",
        "geneafrance.com",
        "geneanet.org",
    )
    _SOCIAL_SPAM_PREFIXES: tuple[str, ...] = (
        "u003",
        "u0022",
        "noreply",
        "no-reply",
        "donotreply",
        "service-avis",
        "mairie",
    )

    def _is_valid_social_email(self, addr: str) -> bool:
        """
        Return True when *addr* passes the social-profile spam filter.

        Args:
            addr: Email address candidate to validate.

        Returns:
            True if the address is not on the social spam blocklist.
        """
        low = addr.lower()
        if any(sp in low for sp in self._SOCIAL_SPAM_DOMAINS):
            return False
        return not any(low.split("@")[0].startswith(pfx) for pfx in self._SOCIAL_SPAM_PREFIXES)

    async def _scrape_social_profile_nodriver(
        self,
        tab: object,
        social_url: str,
        name: str,
    ) -> str | None:
        """
        Navigate directly to a Facebook or Instagram profile and extract an email.

        For Facebook the ``/about`` sub-page is used because it surfaces the
        contact section.  For Instagram the root profile URL is scraped directly.

        Args:
            tab: Active nodriver :class:`Tab` instance.
            social_url: Direct profile URL (must contain ``facebook.com/`` or
                ``instagram.com/``).
            name: Business name (used only for logging).

        Returns:
            First valid email found on the profile page, or ``None``.
        """
        # Facebook /about exposes the contact section; Instagram root is sufficient
        if "facebook.com/" in social_url.lower() and "/about" not in social_url.lower():
            target = social_url.rstrip("/") + "/about"
        else:
            target = social_url

        try:
            await NodriverDom.navigate(tab, target, sleep_s=1.5)
            page_text = await tab.get_content()
            emails = self.extract_emails_from_text(page_text)
            filtered = [e for e in emails if self._is_valid_social_email(e)]
            if filtered:
                logger.info(
                    "Social email for '%s' at %s: %s",
                    name,
                    social_url,
                    filtered[0],
                )
                return filtered[0]
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
            phone: Phone number (optional, used to build a tighter query).

        Returns:
            Email address extracted from the social profile, or ``None``.
        """
        # Build the most targeted query available
        if phone:
            digits = re.sub(r"\D", "", phone)
            if digits.startswith("33") and len(digits) == 11:
                digits = "0" + digits[2:]
            if len(digits) == 10:
                phone_fmt = " ".join(digits[i : i + 2] for i in range(0, 10, 2))
                query = f'"{name}" "{phone_fmt}" facebook OR instagram'
            else:
                query = f'"{name}" "{city}" facebook OR instagram'
        else:
            query = f'"{name}" "{city}" facebook OR instagram'

        search_url = f"https://www.google.com/search?q={quote_plus(query)}&gl=fr&hl=fr"
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
            found = await self._scrape_social_profile_nodriver(tab, profile_url, name)
            if found:
                return found

        return None

    async def find_email_smart(
        self,
        name: str,
        city: str,
        phone: str | None = None,
        social_url: str | None = None,
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

        Returns:
            Email address if found, otherwise None.
        """
        if not NODRIVER_AVAILABLE:
            logger.warning("nodriver not available, skipping smart email search")
            return None

        try:
            return await run_nodriver_task(
                lambda: self._find_email_smart_nodriver(name, city, phone, social_url),
                timeout=120,
            )
        except Exception as exc:
            logger.error("Error in smart email scraper: %s", exc)
            return None

    async def find_email(self, name: str, city: str) -> str | None:
        """
        Find an email address for a business via Google search.

        Always attempts the lookup when a browser engine is available — we
        recover the contact email whenever it is publicly discoverable.
        """
        if not NODRIVER_AVAILABLE:
            logger.warning("nodriver not available, skipping email search")
            return None

        try:
            return await run_nodriver_task(
                lambda: self._find_email_nodriver(name, city),
                timeout=120,
            )
        except Exception as exc:
            logger.error("Error in email scraper: %s", exc)
            return None


email_scraper = EmailScraper()
