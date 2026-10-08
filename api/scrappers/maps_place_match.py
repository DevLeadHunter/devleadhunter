"""
Whether a Google Maps place found by a « nom + ville » search is the prospect's business.

Maps opens the place it thinks the search means, or lists results when it is not sure:
namesakes, neighbours of the same trade, adverts. A place is the business's only when it
carries the business's name (``BusinessName.is_named_like``) and is not in another town; in
a list, the closest name is opened first.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from scrappers.google_scraper import GoogleScraper
from services.decision_maker.normalize import town_key
from services.prospect_search.business_name import BusinessName

MAX_LISTED_PLACES_OPENED: int = 3
_UNKNOWN_CITY: str = "Inconnue"


class MapsSearchOutcome(Enum):
    """What a Maps search gave for the business."""

    OPENED = "opened"
    NOT_LISTED = "not_listed"
    UNREACHABLE = "unreachable"


@dataclass(frozen=True)
class ListedPlace:
    """A place of a Maps results list: the name its card shows and the link opening it."""

    name: str
    link: str


class MapsPlaceMatch:
    """Tells which place of a Maps search is the prospect's business."""

    @staticmethod
    def places_named_like(places: list[ListedPlace], business_name: str, *, town: str | None) -> list[ListedPlace]:
        """
        The listed places named like the business, closest name first.

        Args:
            places: The places of the list, in the list's order.
            business_name: The prospect's business name.
            town: The prospect's town, if known.

        Returns:
            At most ``MAX_LISTED_PLACES_OPENED`` places, by decreasing name similarity, the list's
            order breaking ties.
        """
        named_like: list[tuple[float, int, ListedPlace]] = []
        for position, place in enumerate(places):
            similarity = BusinessName.name_similarity(place.name, business_name, town=town)
            if similarity is not None:
                named_like.append((similarity, position, place))
        named_like.sort(key=lambda match: (-match[0], match[1]))
        return [place for _, _, place in named_like[:MAX_LISTED_PLACES_OPENED]]

    @staticmethod
    def is_in_other_town(address: str | None, *, city: str | None, country: str) -> bool:
        """
        Whether a place's address puts it in another town than the business's.

        Args:
            address: The address the place's panel shows, if any.
            city: The business's town, if known.
            country: The business's country, deciding how the address is read.

        Returns:
            True only when both towns are known and differ: an address naming no town proves nothing.
        """
        if not (address or "").strip() or not (city or "").strip():
            return False
        place_city = GoogleScraper.extract_city(address or "", country)
        if place_city == _UNKNOWN_CITY:
            return False
        return town_key(place_city) != town_key(city or "")
