"""
Target verticals of the Réceptionniste IA prospection.

The receptionist is sold to businesses that receive requests they cannot answer,
with or without a website. The waves decided on 24/09/2026:

1. couvreurs, charpentiers, carrosseries — hands busy, a photo is worth a quote;
2. lieux de mariage, traiteurs — the Sunday 22h request, lost until Monday;
3. agences immobilières — best score, heavier purchase, once the mailbox entry exists.

Each vertical carries the Google Maps search terms that find it and the stems that
recognize it in a scraped ``prospect.category`` (free text, source-dependent).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class SourcingVertical:
    """A trade the receptionist is sold to: how to find it and how to recognize it."""

    key: str
    label: str
    wave: int
    search_terms: tuple[str, ...]
    category_stems: tuple[str, ...]


class SourcingVerticalCatalog:
    """The target verticals and the rule matching a prospect category to one of them."""

    VERTICALS: ClassVar[tuple[SourcingVertical, ...]] = (
        SourcingVertical(
            key="couvreur",
            label="Couvreurs",
            wave=1,
            search_terms=("Couvreur",),
            category_stems=("couvreu", "couverture", "toiture", "zingu"),
        ),
        SourcingVertical(
            key="charpentier",
            label="Charpentiers",
            wave=1,
            search_terms=("Charpentier",),
            category_stems=("charpent",),
        ),
        SourcingVertical(
            key="carrosserie",
            label="Carrosseries",
            wave=1,
            search_terms=("Carrosserie",),
            category_stems=("carross",),
        ),
        SourcingVertical(
            key="lieu-mariage",
            label="Lieux de mariage",
            wave=2,
            search_terms=("Salle de mariage", "Domaine mariage", "Salle de réception"),
            category_stems=("mariage", "salle de reception", "lieu de reception", "domaine de reception"),
        ),
        SourcingVertical(
            key="traiteur",
            label="Traiteurs",
            wave=2,
            search_terms=("Traiteur",),
            category_stems=("traiteur",),
        ),
        SourcingVertical(
            key="agence-immobiliere",
            label="Agences immobilières",
            wave=3,
            search_terms=("Agence immobilière",),
            category_stems=("immobili",),
        ),
    )

    @classmethod
    def match(cls, category: str | None) -> SourcingVertical | None:
        """
        Find the target vertical a scraped category belongs to.

        Matching is accent- and case-insensitive on stems, so "Entreprise de toiture"
        and "COUVREUR ZINGUEUR" both land on couvreur.

        Args:
            category: Raw ``prospect.category``.

        Returns:
            The first matching vertical, or None when the category is not a target.
        """
        if not category:
            return None
        normalized = cls.normalize(category)
        for vertical in cls.VERTICALS:
            if any(stem in normalized for stem in vertical.category_stems):
                return vertical
        return None

    @staticmethod
    def normalize(category: str) -> str:
        """Lower-case a category and drop its diacritics, for stem matching."""
        decomposed = unicodedata.normalize("NFD", category.lower())
        return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
