"""
Swiss directory — the search.ch entry of a Swiss business, read by its phone number.

search.ch publishes, for each subscriber, what the business gave the directory: its
email, its website, its mobile numbers, and the asterisk of a subscriber who refuses
advertising. Swiss law forbids advertising to such a subscriber (LCD art. 3 al. 1
let. u), so a search reads the asterisk before proposing the business. The directory
is read the way a person checks a listing: by the number the business already showed,
or by its name in its town, or its owner's name at its address, when that number is not
listed; it is never listed in bulk. A number search.ch does not list is looked up on
zip.ch too, which keeps the entries the directory dropped, asterisk included.
"""

from __future__ import annotations

import asyncio
import html
import logging
import re
import time
from dataclasses import dataclass
from typing import ClassVar

import httpx

from services.sms.phone_normalizer import PhoneNumberPlans, to_e164
from services.website_liveness_service import website_liveness_service

logger = logging.getLogger(__name__)

_BASE_URL: str = "https://search.ch"
_ZIP_RESULTS_URL: str = "https://zip.ch/fr/results/"
_SWISS_DIAL_CODE: str = "+41"
_TIMEOUT_SECONDS: float = 10.0
_SECONDS_BETWEEN_REQUESTS: float = 1.0
_REFUSED_STATUSES: frozenset[int] = frozenset({429, 503})
_SECONDS_AFTER_REFUSAL: float = 20.0
_ATTEMPTS_AFTER_REFUSAL: int = 2
_ENTRY_PATH_RE: re.Pattern[str] = re.compile(
    r'href="(/tel/(?!edit|extended|itjs|vcard|opensearch|s/)[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+)"'
)
_VCARD_PATH_RE: re.Pattern[str] = re.compile(r'(/tel/vcard/[^"]+?\.vcf\?key=[0-9a-f]+)')
_TITLE_RE: re.Pattern[str] = re.compile(r"<title>([^<]+)</title>")
_NO_ADVERTISING_NUMBER_RE: re.Pattern[str] = re.compile(
    r'href="tel:[^"]+"[^>]*>[^<]*(?:\*</a>|</a>\s*<span[^>]*>\s*\*\s*</span>)'
)
_VCARD_LINE_RE: re.Pattern[str] = re.compile(r"^(EMAIL|URL|TEL)[^:\n]*:(.+)$", re.MULTILINE)
_VCARD_FOLD_RE: re.Pattern[str] = re.compile(r"\r?\n[ \t]")
_BUSINESS_ENTRY_MARK: str = 'data-entrytype="Business"'
_NOT_LISTED_STATUS: int = 404
_RESULT_LIST_RE: re.Pattern[str] = re.compile(r'<ol class="tel-results tel-entries">(.*?)</ol>', re.DOTALL)
_RESULT_ENTRY_START_RE: re.Pattern[str] = re.compile(r'<li class="tel-(?=person|commercial)')
_RESULT_ENTRY_NAME_RE: re.Pattern[str] = re.compile(r'<h1><a href="(/tel/[^"]+)"[^>]*>([^<]+)</a></h1>')
_RESULT_ENTRY_EXTRA_LINE_RE: re.Pattern[str] = re.compile(
    r'<div class="tel-context">(?:<span[^>]*>[^<]*</span>)?([^<]*)</div>'
)


@dataclass(frozen=True)
class SwissDirectoryEntry:
    """What the directory lists for one subscriber."""

    url: str
    name: str
    is_business: bool
    refuses_advertising: bool
    emails: tuple[str, ...]
    websites: tuple[str, ...]
    mobile_phones: tuple[str, ...]
    extra_line: str = ""


class SwissDirectoryUnavailableError(Exception):
    """search.ch did not answer: whether the subscriber refuses advertising stays unknown."""


class SwissDirectory:
    """Reads one search.ch entry, found by the phone number a business already showed, by its name or at its address."""

    _next_request_slot: ClassVar[float] = 0.0

    async def entry_for_phone(self, phone: str | None) -> SwissDirectoryEntry | None:
        """
        The directory entry that lists a Swiss phone number.

        Args:
            phone: The number as the business wrote it.

        A number listed once opens its entry page at once; listed several times, it opens the list
        of entries, and the first one is read.

        Returns:
            The entry, or ``None`` for a number that is not Swiss or not listed.

        Raises:
            SwissDirectoryUnavailableError: The directory did not answer.
        """
        national_number = self.national_number(phone)
        if national_number is None:
            return None
        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT_SECONDS,
                follow_redirects=True,
                headers=website_liveness_service.REQUEST_HEADERS,
            ) as http:
                page = await self._get(http, f"{_BASE_URL}/tel/", params={"was": national_number, "lang": "fr"})
                if page.status_code == _NOT_LISTED_STATUS:
                    return None
                self._raise_unless_answered(page)
                entry_url = str(page.url)
                entry_path = None if _VCARD_PATH_RE.search(page.text) else _ENTRY_PATH_RE.search(page.text)
                if entry_path is not None:
                    entry_url = f"{_BASE_URL}{entry_path.group(1)}.fr.html"
                    page = await self._get(http, entry_url)
                    self._raise_unless_answered(page)
                vcard_path = _VCARD_PATH_RE.search(page.text)
                vcard = (
                    await self._get(http, f"{_BASE_URL}{html.unescape(vcard_path.group(1))}") if vcard_path else None
                )
        except httpx.HTTPError as exc:
            raise SwissDirectoryUnavailableError(f"search.ch lookup of {national_number} failed: {exc}") from exc
        vcard_text = vcard.text if vcard is not None and vcard.status_code == 200 else ""
        return self.parse_entry(entry_url, page.text, vcard_text)

    async def zip_listing_with_asterisk(self, phone: str | None) -> str | None:
        """
        The zip.ch page that prints the asterisk after a number, for a number search.ch does not list.

        zip.ch copies the directory and keeps the entries it dropped, with the asterisk their
        subscriber asked for. A page that does not answer proves nothing either way.

        Args:
            phone: The number as the business wrote it.

        Returns:
            The address of the zip.ch results page showing the starred number, else ``None``.
        """
        national_number = self.national_number(phone)
        if national_number is None:
            return None
        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT_SECONDS,
                follow_redirects=True,
                headers=website_liveness_service.REQUEST_HEADERS,
            ) as http:
                page = await http.get(_ZIP_RESULTS_URL, params={"q": national_number})
        except httpx.HTTPError as exc:
            logger.info("zip.ch lookup of %s failed: %s", national_number, exc)
            return None
        international_number = f"{_SWISS_DIAL_CODE}{national_number[1:]}"
        starred_number = re.compile(
            rf'href="tel:{re.escape(international_number)}"[^>]*>.*?</a>\s*<span[^>]*>(?:&nbsp;|\s)*\*\s*</span>',
            re.DOTALL,
        )
        if page.status_code != 200 or starred_number.search(page.text) is None:
            return None
        return str(page.url)

    @classmethod
    async def _get(cls, http: httpx.AsyncClient, url: str, *, params: dict[str, str] | None = None) -> httpx.Response:
        """
        One request to search.ch, spaced from the previous one, asked again after a refusal.

        search.ch answers a burst of lookups with « too many requests »: a refused page is asked
        again after a pause, a couple of times, before the lookup is given up.
        """
        await cls._wait_for_turn()
        page = await http.get(url, params=params)
        for _ in range(_ATTEMPTS_AFTER_REFUSAL):
            if page.status_code not in _REFUSED_STATUSES:
                return page
            await asyncio.sleep(_SECONDS_AFTER_REFUSAL)
            await cls._wait_for_turn()
            page = await http.get(url, params=params)
        if page.status_code in _REFUSED_STATUSES:
            logger.warning("search.ch still refuses %s (status %s)", url, page.status_code)
        return page

    @classmethod
    async def _wait_for_turn(cls) -> None:
        """Wait for the next free slot: the lookups of candidates verified side by side take turns."""
        now = time.monotonic()
        slot = max(now, cls._next_request_slot)
        cls._next_request_slot = slot + _SECONDS_BETWEEN_REQUESTS
        await asyncio.sleep(slot - now)

    @staticmethod
    def _raise_unless_answered(page: httpx.Response) -> None:
        """Stop a lookup the directory refused (rate limit, outage): an unread page proves nothing."""
        if page.status_code != 200:
            raise SwissDirectoryUnavailableError(f"search.ch answered {page.status_code} for {page.url}")

    async def entry_at(self, entry_url: str) -> SwissDirectoryEntry:
        """
        Read the entry page of one subscriber and its vCard.

        Args:
            entry_url: Address of the entry page, as a result list gives it.

        Returns:
            The entry.

        Raises:
            SwissDirectoryUnavailableError: The directory did not answer.
        """
        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT_SECONDS,
                follow_redirects=True,
                headers=website_liveness_service.REQUEST_HEADERS,
            ) as http:
                page = await self._get(http, entry_url)
                self._raise_unless_answered(page)
                vcard_path = _VCARD_PATH_RE.search(page.text)
                vcard = (
                    await self._get(http, f"{_BASE_URL}{html.unescape(vcard_path.group(1))}") if vcard_path else None
                )
        except httpx.HTTPError as exc:
            raise SwissDirectoryUnavailableError(f"search.ch entry {entry_url} failed: {exc}") from exc
        vcard_text = vcard.text if vcard is not None and vcard.status_code == 200 else ""
        return self.parse_entry(entry_url, page.text, vcard_text)

    async def entries_for_name(self, name: str, town: str) -> list[SwissDirectoryEntry]:
        """
        The entries the directory lists for a name in a town, as its result list shows them.

        The directory finds the name anywhere in an entry, the owner written on its extra line
        included. Only the list is read: each entry's name, extra line and asterisk.

        Args:
            name: The business name as its listing writes it.
            town: The business's town.

        Returns:
            The entries, empty when nothing is listed.

        Raises:
            SwissDirectoryUnavailableError: The directory did not answer.
        """
        if not name.strip() or not town.strip():
            return []
        return await self._listed_entries({"was": name, "wo": town}, lookup=f"{name} in {town}")

    async def entries_at_address(self, name_word: str, address: str) -> list[SwissDirectoryEntry]:
        """
        The entries the directory lists under a word of a name along a street, as its result list shows them.

        A sole trader often lists the business number on the entry of their own name, which
        the business name does not find (« F. Rochat Sàrl » under « Rochat, Paul »).

        Args:
            name_word: The word of the business name the entry carries, its owner's family name.
            address: The business's street address.

        Returns:
            The entries, empty when nothing is listed.

        Raises:
            SwissDirectoryUnavailableError: The directory did not answer.
        """
        if not name_word.strip() or not address.strip():
            return []
        return await self._listed_entries({"was": name_word, "wo": address}, lookup=f"{name_word} at {address}")

    async def _listed_entries(self, query: dict[str, str], *, lookup: str) -> list[SwissDirectoryEntry]:
        """Run one search of the directory: a single entry opens at once, several make a result list."""
        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT_SECONDS,
                follow_redirects=True,
                headers=website_liveness_service.REQUEST_HEADERS,
            ) as http:
                page = await self._get(http, f"{_BASE_URL}/tel/", params={**query, "lang": "fr"})
        except httpx.HTTPError as exc:
            raise SwissDirectoryUnavailableError(f"search.ch lookup of {lookup} failed: {exc}") from exc
        if page.status_code == _NOT_LISTED_STATUS:
            return []
        self._raise_unless_answered(page)
        if _VCARD_PATH_RE.search(page.text):
            return [self.parse_entry(str(page.url), page.text, "")]
        return self.parse_result_list(page.text)

    @staticmethod
    def parse_result_list(page_html: str) -> list[SwissDirectoryEntry]:
        """
        Read the entries of a result list, the paid ones beside it left out.

        Args:
            page_html: The result page.

        Returns:
            One entry per listed subscriber, without its email or website (the list shows neither).
        """
        result_list = _RESULT_LIST_RE.search(page_html)
        if result_list is None:
            return []
        entries: list[SwissDirectoryEntry] = []
        for block in _RESULT_ENTRY_START_RE.split(result_list.group(1))[1:]:
            name_link = _RESULT_ENTRY_NAME_RE.search(block)
            if name_link is None:
                continue
            extra_line = _RESULT_ENTRY_EXTRA_LINE_RE.search(block)
            entries.append(
                SwissDirectoryEntry(
                    url=f"{_BASE_URL}{name_link.group(1)}.fr.html",
                    name=html.unescape(name_link.group(2)).strip(),
                    is_business=block.startswith("commercial"),
                    refuses_advertising=_NO_ADVERTISING_NUMBER_RE.search(block) is not None,
                    emails=(),
                    websites=(),
                    mobile_phones=(),
                    extra_line=html.unescape(extra_line.group(1)).strip() if extra_line else "",
                )
            )
        return entries

    @staticmethod
    def national_number(phone: str | None) -> str | None:
        """The ten digits a Swiss number is searched by (« 0219229168 »), ``None`` for any other number."""
        international = to_e164(phone, country="CH")
        if international is None or not international.startswith(_SWISS_DIAL_CODE):
            return None
        return f"0{international.removeprefix(_SWISS_DIAL_CODE)}"

    @staticmethod
    def parse_entry(entry_url: str, page_html: str, vcard_text: str) -> SwissDirectoryEntry:
        """
        Read an entry page and its vCard.

        Args:
            entry_url: Address of the entry page.
            page_html: The entry page, where a number refusing advertising ends with an asterisk.
            vcard_text: The entry's vCard, empty when the directory gave none.

        Returns:
            The entry's facts.
        """
        title = _TITLE_RE.search(page_html)
        name = html.unescape(title.group(1)).split(" - search.ch")[0].strip() if title else ""
        emails: list[str] = []
        websites: list[str] = []
        mobile_phones: list[str] = []
        for field_name, raw_value in _VCARD_LINE_RE.findall(_VCARD_FOLD_RE.sub("", vcard_text)):
            value = raw_value.strip()
            if field_name == "EMAIL":
                emails.append(value.lower())
            elif field_name == "URL" and "search.ch/" not in value:
                websites.append(value)
            elif field_name == "TEL" and PhoneNumberPlans.mobile_of_country(value, country="CH") is not None:
                mobile_phones.append(value)
        return SwissDirectoryEntry(
            url=entry_url,
            name=name,
            is_business=_BUSINESS_ENTRY_MARK in page_html,
            refuses_advertising=_NO_ADVERTISING_NUMBER_RE.search(page_html) is not None,
            emails=tuple(emails),
            websites=tuple(websites),
            mobile_phones=tuple(mobile_phones),
        )


swiss_directory = SwissDirectory()
