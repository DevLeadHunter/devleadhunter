"""
Swiss directory — the search.ch entry of a Swiss business, read by its phone number.

search.ch publishes, for each subscriber, what the business gave the directory: its
email, its website, its mobile numbers, and the asterisk of a subscriber who refuses
advertising. Swiss law forbids advertising to such a subscriber (LCD art. 3 al. 1
let. u), so a search reads the asterisk before proposing the business. The directory
is read one entry at a time, by the number the business already showed, the way a
person checks a listing; it is never listed in bulk.
"""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass

import httpx

from services.sms.phone_normalizer import PhoneNumberPlans, to_e164
from services.website_liveness_service import website_liveness_service

logger = logging.getLogger(__name__)

_BASE_URL: str = "https://search.ch"
_SWISS_DIAL_CODE: str = "+41"
_TIMEOUT_SECONDS: float = 10.0
_ENTRY_PATH_RE: re.Pattern[str] = re.compile(
    r'href="(/tel/(?!edit|extended|itjs|vcard|opensearch|s/)[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+)"'
)
_VCARD_PATH_RE: re.Pattern[str] = re.compile(r'(/tel/vcard/[^"]+?\.vcf\?key=[0-9a-f]+)')
_TITLE_RE: re.Pattern[str] = re.compile(r"<title>([^<]+)</title>")
_NO_ADVERTISING_NUMBER_RE: re.Pattern[str] = re.compile(r'href="tel:[^"]+"[^>]*>[^<]*\*</a>')
_VCARD_LINE_RE: re.Pattern[str] = re.compile(r"^(EMAIL|URL|TEL)[^:\n]*:(.+)$", re.MULTILINE)
_VCARD_FOLD_RE: re.Pattern[str] = re.compile(r"\r?\n[ \t]")
_BUSINESS_ENTRY_MARK: str = 'data-entrytype="Business"'


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


class SwissDirectory:
    """Reads one search.ch entry, found by the phone number a business already showed."""

    async def entry_for_phone(self, phone: str | None) -> SwissDirectoryEntry | None:
        """
        The directory entry that lists a Swiss phone number.

        Args:
            phone: The number as the business wrote it.

        Returns:
            The entry, or ``None`` for a number that is not Swiss, not listed, or a directory that does not answer.
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
                listing = await http.get(f"{_BASE_URL}/tel/", params={"was": national_number})
                entry_path = _ENTRY_PATH_RE.search(listing.text) if listing.status_code == 200 else None
                if entry_path is None:
                    return None
                entry_url = f"{_BASE_URL}{entry_path.group(1)}.fr.html"
                page = await http.get(entry_url)
                if page.status_code != 200:
                    return None
                vcard_path = _VCARD_PATH_RE.search(page.text)
                vcard = await http.get(f"{_BASE_URL}{html.unescape(vcard_path.group(1))}") if vcard_path else None
        except httpx.HTTPError as exc:
            logger.info("search.ch lookup of %s failed: %s", national_number, exc)
            return None
        vcard_text = vcard.text if vcard is not None and vcard.status_code == 200 else ""
        return self.parse_entry(entry_url, page.text, vcard_text)

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
