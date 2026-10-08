"""
Which places of a Google Maps results list can be the prospect's business.

A « nom + ville » search that Maps cannot settle on one place lands on a list of results:
namesakes, neighbours of the same trade, adverts. The first one is often none of them the
business, so a listed place is opened only when it carries the business's name, the
closest name first, and a place whose address puts it in another town is passed over.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from scrappers.google_scraper import GoogleScraper
from services.decision_maker.normalize import company_tokens, join_dotted_initials, town_key
from services.prospect_search.business_name import COMMON_NAME_WORDS, NAME_LINK_WORDS, BusinessName
from services.prospect_search.trade_catalog import TradeCatalog

MIN_LISTED_NAME_SIMILARITY: float = 0.5
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


class MapsSearchResults:
    """Tells which places of a Maps results list can be the prospect's business."""

    @classmethod
    def places_named_like(cls, places: list[ListedPlace], business_name: str, *, town: str | None) -> list[ListedPlace]:
        """
        The listed places named like the business (see ``is_named_like``), closest name first.

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
            similarity = cls._name_similarity(place.name, business_name, town=town)
            if similarity is not None:
                named_like.append((similarity, position, place))
        named_like.sort(key=lambda match: (-match[0], match[1]))
        return [place for _, _, place in named_like[:MAX_LISTED_PLACES_OPENED]]

    @classmethod
    def is_named_like(cls, place_name: str, business_name: str, *, town: str | None) -> bool:
        """
        Whether a place's name is the business's name.

        Only the words that tell a business apart are compared: no legal form, trade word, linking word
        or town, and no tagline (« Exemple Électrique - Maître Électricien Laval »). Most of them must be
        the same (« Exemple & Fils Électricité Générale » is « Exemple Et Fils »). A business named after
        one such word (« Exemple ») matches no place adding a word of its own: « Exemple Électricité » is
        it, « Exemple Jules », a podiatrist, is not; nor is a namesake sharing a first name (« Jules
        Exemple » for « Jules Modèle »). A name saying only a trade and a town (« Garage de Morges »)
        must be the place's name word for word.

        Args:
            place_name: The name the place shows.
            business_name: The prospect's business name.
            town: The prospect's town, if known.

        Returns:
            True when the place carries the business's name.
        """
        return cls._name_similarity(place_name, business_name, town=town) is not None

    @classmethod
    def _name_similarity(cls, place_name: str, business_name: str, *, town: str | None) -> float | None:
        """The share of distinctive words the two names have in common, or None when they name two businesses."""
        business_words = cls._name_words(business_name)
        place_words = cls._name_words(BusinessName.clean(place_name))
        town_words = company_tokens(town or "")
        business_distinctive = cls._distinctive(business_words) - town_words
        place_distinctive = cls._distinctive(place_words) - town_words
        if not business_distinctive:
            return 1.0 if business_words and place_words == business_words else None
        shared = business_distinctive & place_distinctive
        similarity = len(shared) / len(business_distinctive | place_distinctive)
        adds_own_word = bool(place_distinctive - business_distinctive)
        if similarity < MIN_LISTED_NAME_SIMILARITY or (len(business_distinctive) == 1 and adds_own_word):
            return None
        return similarity

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

    @staticmethod
    def _name_words(name: str) -> set[str]:
        """The words of a name, its legal form left out (« inc », « Sàrl ») and its dotted initials joined."""
        return company_tokens(join_dotted_initials(BusinessName.without_legal_form(name)))

    @staticmethod
    def _distinctive(words: set[str]) -> set[str]:
        """The words that tell a business from another: no trade word, no word common to many names, no link word."""
        return {
            word
            for word in words
            if word not in COMMON_NAME_WORDS and word not in NAME_LINK_WORDS and not TradeCatalog.is_trade_word(word)
        }
