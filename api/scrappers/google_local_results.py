"""
Google local results reader — the « Lieux » tab, 20 businesses per page.

One page tells, for each business: name, category, town, phone, rating, number of
reviews, whether it is closed for good, and whether Google shows a « Site Web »
button. It is fetched as plain HTML through the Bright Data Web Unlocker, so the
discovery needs no browser and runs on the server.

The markup is read by structure (heading role, line order, link targets), never by
Google's obfuscated class names alone: when the card layout is not recognised the
parser returns nothing and the caller falls back on Bright Data's parsed JSON, which
carries fewer fields (no phone, no website flag).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote_plus

from bs4 import BeautifulSoup, Tag

from scrappers.google_scraper import GoogleScraper
from services.sms.phone_normalizer import to_e164

_RATING_LINE_RE: re.Pattern[str] = re.compile(r"^(\d[.,]\d)\s*\(([\d\s\u202f\u00a0.,]+)\)")
_FEATURE_ID_RE: re.Pattern[str] = re.compile(r"!1s0x[0-9a-f]+:0x([0-9a-f]+)", re.IGNORECASE)
_PHONE_SHAPE_RE: re.Pattern[str] = re.compile(r"^\+?\(?\d[\d\s().\-]{6,18}\d$")
_PERMANENTLY_CLOSED_MARKERS: tuple[str, ...] = ("définitivement fermé", "fermé définitivement", "permanently closed")
_TEMPORARILY_CLOSED_MARKERS: tuple[str, ...] = ("fermé temporairement", "temporairement fermé", "temporarily closed")
_OPENING_PREFIXES: tuple[str, ...] = ("ouvert", "fermé", "ouvre", "ferme", "open", "closed", "opens", "closes")
_SENIORITY_MARKERS: tuple[str, ...] = ("en activité", "in business")
_WEBSITE_BUTTON_LABELS: frozenset[str] = frozenset({"site web", "website", "site internet"})
_PROVINCE_SUFFIX_RE: re.Pattern[str] = re.compile(r",\s*(QC|Québec|Quebec)$", re.IGNORECASE)
_STREET_SEGMENT_RE: re.Pattern[str] = re.compile(
    r"^(\d|(rue|av|avenue|bd|boulevard|chemin|ch|route|rte|place|pl|impasse|all[ée]e|quai|cours|square|passage"
    r"|zone|za|zi|zac|lieu-dit|rang|mont[ée]e)[\s.])",
    re.IGNORECASE,
)


@dataclass
class LocalListing:
    """One business of a Google local results page."""

    name: str
    category: str | None = None
    locality: str | None = None
    address: str | None = None
    phone: str | None = None
    rating: float | None = None
    reviews_count: int | None = None
    # None when the page was read from the parsed JSON, which does not carry the button.
    has_website_button: bool | None = None
    is_permanently_closed: bool = False
    is_temporarily_closed: bool = False
    cid: str | None = None

    @property
    def maps_url(self) -> str | None:
        """Link to the Google Maps listing, built from Google's identifier."""
        return f"https://www.google.com/maps?cid={self.cid}" if self.cid else None


class GoogleLocalResultsParser:
    """Turns a Google local results page into :class:`LocalListing` rows."""

    @classmethod
    def parse_html(cls, html: str, *, country: str = "FR") -> list[LocalListing]:
        """
        Read every business card of a local results page.

        Args:
            html: Raw page HTML.
            country: ISO code of the search country, deciding the phone and address shapes.

        Returns:
            The listings in page order; empty when the card layout is not recognised.
        """
        soup = BeautifulSoup(html, "html.parser")
        listings: list[LocalListing] = []
        seen_names: set[str] = set()
        for details in soup.select("div.rllt__details"):
            listing = cls._read_card(details, country)
            if listing is None or listing.name.lower() in seen_names:
                continue
            seen_names.add(listing.name.lower())
            listings.append(listing)
        if not any(listing.has_website_button or listing.cid for listing in listings):
            # Some country layouts carry no action link at all: the website is then unknown, not absent.
            for listing in listings:
                listing.has_website_button = None
        return listings

    @classmethod
    def parse_snack_pack(cls, snack_pack: list[dict[str, Any]]) -> list[LocalListing]:
        """
        Read the parsed JSON of a local results page (fallback of :meth:`parse_html`).

        Args:
            snack_pack: The ``snack_pack`` list of Bright Data's parsed page.

        Returns:
            The listings, without phone nor website flag (the JSON does not carry them).
        """
        listings: list[LocalListing] = []
        for place in snack_pack:
            name = str(place.get("name") or "").strip()
            if not name or place.get("sponsored"):
                continue
            status_text = f"{place.get('work_status') or ''} {place.get('work_status_details') or ''}".lower()
            rating = place.get("rating")
            reviews_count = place.get("reviews_cnt")
            listings.append(
                LocalListing(
                    name=name,
                    category=str(place.get("type") or "").strip() or None,
                    locality=cls._locality_of(str(place.get("address") or "")),
                    rating=float(rating) if isinstance(rating, int | float) else None,
                    reviews_count=int(reviews_count) if isinstance(reviews_count, int | float) else None,
                    is_permanently_closed=any(marker in status_text for marker in _PERMANENTLY_CLOSED_MARKERS),
                    is_temporarily_closed=any(marker in status_text for marker in _TEMPORARILY_CLOSED_MARKERS),
                    cid=str(place["cid"]) if place.get("cid") else None,
                )
            )
        return listings

    @classmethod
    def _read_card(cls, details: Tag, country: str) -> LocalListing | None:
        """Build a listing from one card's details block, or ``None`` when it has no name."""
        heading = details.find(attrs={"role": "heading"})
        name = heading.get_text(" ", strip=True) if isinstance(heading, Tag) else ""
        if not name:
            return None
        listing = LocalListing(name=name, has_website_button=False)

        lines = [
            child.get_text(" ", strip=True).replace("\u00a0", " ")
            for child in details.find_all("div", recursive=False)
            if child is not heading
        ]
        card_text = " ".join(lines).lower()
        listing.is_permanently_closed = any(marker in card_text for marker in _PERMANENTLY_CLOSED_MARKERS)
        listing.is_temporarily_closed = any(marker in card_text for marker in _TEMPORARILY_CLOSED_MARKERS)

        for position, line in enumerate(lines):
            segments = [segment.strip() for segment in line.split("·") if segment.strip()]
            if position == 0:
                cls._read_rating_line(listing, segments)
                continue
            for segment in segments:
                if listing.phone is None and cls._is_phone(segment, country):
                    listing.phone = segment
                elif position == 1 and listing.locality is None and cls._is_locality(segment):
                    if _STREET_SEGMENT_RE.match(segment):
                        # In the searched town itself Google shows the street, not the town.
                        listing.address = segment
                    else:
                        listing.locality = _PROVINCE_SUFFIX_RE.sub("", segment).strip()

        card = cls._card_of(details)
        cls._read_links(listing, card, country)
        return listing

    @staticmethod
    def _read_rating_line(listing: LocalListing, segments: list[str]) -> None:
        """Read « 5,0 (17) · Paysagiste » (or « Aucun avis · Paysagiste ») into the listing."""
        if not segments:
            return
        match = _RATING_LINE_RE.match(segments[0])
        if match:
            listing.rating = float(match.group(1).replace(",", "."))
            digits = re.sub(r"\D", "", match.group(2))
            listing.reviews_count = int(digits) if digits else None
        if len(segments) > 1:
            listing.category = segments[-1]
        elif not match and not segments[0].lower().startswith(("aucun avis", "no reviews")):
            listing.category = segments[0]

    @staticmethod
    def _is_phone(segment: str, country: str) -> bool:
        """Whether a line segment is a phone number of the search country."""
        return bool(_PHONE_SHAPE_RE.match(segment)) and to_e164(segment, country=country) is not None

    @staticmethod
    def _is_locality(segment: str) -> bool:
        """Whether a segment of the second line names the town (not the opening status nor the seniority)."""
        lowered = segment.lower()
        if any(marker in lowered for marker in _SENIORITY_MARKERS):
            return False
        return not lowered.startswith(_OPENING_PREFIXES)

    @staticmethod
    def _locality_of(address_line: str) -> str | None:
        """Town part of the parsed JSON's address line (« Plus de 7 ans en activité ⋅ Sion »)."""
        segments = [segment.strip() for segment in re.split(r"[⋅·]", address_line) if segment.strip()]
        towns = [segment for segment in segments if not any(marker in segment.lower() for marker in _SENIORITY_MARKERS)]
        return _PROVINCE_SUFFIX_RE.sub("", towns[-1]).strip() if towns else None

    @staticmethod
    def _card_of(details: Tag) -> Tag:
        """Smallest ancestor holding the card's action links (« Site Web », « Itinéraire »)."""
        node: Tag = details
        for _ in range(8):
            parent = node.parent
            if not isinstance(parent, Tag):
                break
            if len(parent.select("div.rllt__details")) > 1:
                break
            node = parent
        return node

    @classmethod
    def _read_links(cls, listing: LocalListing, card: Tag, country: str) -> None:
        """Read the website button and the directions link (address, Google identifier) of a card."""
        for anchor in card.find_all("a"):
            href = str(anchor.get("href") or anchor.get("data-url") or "")
            label = anchor.get_text(" ", strip=True).lower()
            if label in _WEBSITE_BUTTON_LABELS or href.startswith("/goto?"):
                listing.has_website_button = True
            if "/maps/dir/" not in href:
                continue
            feature_id = _FEATURE_ID_RE.search(href)
            if feature_id:
                listing.cid = str(int(feature_id.group(1), 16))
            destination = unquote_plus(href.split("/maps/dir//", 1)[-1].split("/data=", 1)[0])
            address = destination[len(listing.name) :].lstrip(", ") if destination.startswith(listing.name) else ""
            if address:
                listing.address = address
                town = GoogleScraper.extract_city(address, country)
                if town and town != "Inconnue":
                    listing.locality = town
