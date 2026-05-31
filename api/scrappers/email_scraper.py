"""
Email scraper using Google search to find contact emails (nodriver).
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import quote_plus

from scrappers.nodriver_browser import NODRIVER_AVAILABLE, NodriverBrowser, _env_bool
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
        self.email_pattern = re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        )

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
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not handle Google cookie consent: %s", exc)

    async def search_google_page(
        self, tab: object, query: str, page_number: int = 0
    ) -> Optional[str]:
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
                search_url = (
                    f"https://www.google.com/search?q={quote_plus(query)}&start={start_param}"
                )

            await NodriverDom.navigate(tab, search_url, sleep_s=0.5)

            if page_number == 0:
                await self.accept_google_cookies(tab)
                await asyncio.sleep(0.5)

            page_text = await tab.get_content()
            emails = self.extract_emails_from_text(page_text)

            if emails:
                spam_domains = [
                    "example.com",
                    "test.com",
                    "domain.com",
                    "yoursite.com",
                    "google.com",
                    "gstatic.com",
                    "facebook.com",
                ]
                filtered = [
                    email
                    for email in emails
                    if not any(spam in email.lower() for spam in spam_domains)
                ]
                if filtered:
                    logger.info(
                        "Found email(s) for query '%s' page %s: %s",
                        query,
                        page_number + 1,
                        filtered,
                    )
                    return filtered[0]
            return None
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "Error searching Google page %s for '%s': %s", page_number + 1, query, exc
            )
            return None

    async def search_google_multiple_pages(
        self, tab: object, query: str, max_pages: int = 3
    ) -> Optional[str]:
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

    async def _find_email_nodriver(self, name: str, city: str) -> Optional[str]:
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

    async def find_email(self, name: str, city: str) -> Optional[str]:
        """
        Find an email address for a business via Google search.

        Skipped when ``SCRAPER_INLINE_EMAIL=false`` (default) to keep bulk scrapes
        fast and avoid opening a second Chrome alongside the main scraper.
        """
        try:
            from core.config import settings

            if not settings.scraper_inline_email:
                return None
        except Exception:  # noqa: BLE001
            if not _env_bool("SCRAPER_INLINE_EMAIL", default=False):
                return None

        if not NODRIVER_AVAILABLE:
            logger.warning("nodriver not available, skipping email search")
            return None

        try:
            return await run_nodriver_task(
                lambda: self._find_email_nodriver(name, city),
                timeout=120,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Error in email scraper: %s", exc)
            return None


email_scraper = EmailScraper()
