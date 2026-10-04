"""
Business name — from a listing title to the name customers know the business by.

Google listings are often written for the search engine: « A.G Rénovation Couvreur -
Réparation de toiture, Démoussage, Velux », « SB Rénovation | Couvreur Dijon »,
« Cadiou Couverture (couvreur Dijon 21) ». The prospect, and every message written to
it afterwards, must carry the name alone.
"""

from __future__ import annotations

import re
import unicodedata

_PARENTHESES_RE: re.Pattern[str] = re.compile(r"\([^)]*\)")
# A separator set off by spaces opens a tagline; a hyphen inside a name (« Weiss-Couvreur ») does not.
_TAGLINE_SEPARATOR_RE: re.Pattern[str] = re.compile(r"\s+[-–—|:/·•]+(?:\s+|$)|,\s+")
_SPACES_RE: re.Pattern[str] = re.compile(r"\s+")
_EDGE_PUNCTUATION: str = " -–—|,;:/·•"
_MINIMUM_NAME_WORDS: int = 2
# Letters, digits, spaces and punctuation make a name; pictographs and trademark signs decorate it.
_NAME_CHARACTER_CATEGORIES: frozenset[str] = frozenset({"L", "N", "Z", "P"})
_KEPT_SYMBOLS: frozenset[str] = frozenset({"+", "|"})


class BusinessName:
    """Cleans the name a listing gives a business."""

    @classmethod
    def clean(cls, listing_name: str) -> str:
        """
        Keep the business name of a listing title, without its decoration and its tagline.

        Args:
            listing_name: The name as the listing writes it.

        Returns:
            The name alone; the listing name, trimmed, when nothing name-like remains.
        """
        name = cls._without_decoration(unicodedata.normalize("NFC", listing_name))
        name = _PARENTHESES_RE.sub(" ", name)
        head = _TAGLINE_SEPARATOR_RE.split(name, maxsplit=1)[0]
        # A lone word before the separator is a trade (« Garage - Carrosserie Dupont »), not a name.
        if len(head.split()) >= _MINIMUM_NAME_WORDS:
            name = head
        name = _SPACES_RE.sub(" ", name).strip(_EDGE_PUNCTUATION)
        return name or listing_name.strip()

    @staticmethod
    def _without_decoration(name: str) -> str:
        """Drop pictographs, trademark signs and invisible joiners; each leaves a space."""
        return "".join(
            character
            if unicodedata.category(character)[0] in _NAME_CHARACTER_CATEGORIES or character in _KEPT_SYMBOLS
            else " "
            for character in name
        )
