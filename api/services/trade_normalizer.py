"""Turn a scraped business category into a natural French trade word for ``{metier}``.

``prospect.category`` is free text from Google Maps / PagesJaunes / OSM — e.g.
"Atelier de réparation automobile", "Salon de coiffure, Barbier", or the generic
"Entreprise" / "Inconnu" fallbacks the scrapers write. Injected raw into ``{metier}``
it reads wrong ("chercher un Atelier de réparation automobile à Lyon"). This maps
the common local trades to the word a client would actually use ("garagiste"), and
falls back to a lightly cleaned form (or a neutral "professionnel") otherwise.
"""

from __future__ import annotations

import re

from services.text_normalizer import TextNormalizer

# First matching keyword wins, so keep the most specific terms first. Keys are
# matched as substrings on the accent-stripped, lower-cased category, so
# "reparation automobile" catches "Atelier de réparation automobile".
_TRADE_BY_KEYWORD: tuple[tuple[str, str], ...] = (
    ("reparation automobile", "garagiste"),
    ("garage", "garagiste"),
    ("mecanique", "garagiste"),
    ("carross", "carrossier"),
    ("plomb", "plombier"),
    ("chauffagi", "chauffagiste"),
    ("electric", "électricien"),
    ("barbier", "barbier"),
    ("barber", "barbier"),
    ("coiffure", "coiffeur"),
    ("coiffeur", "coiffeur"),
    ("dentaire", "dentiste"),
    ("dentiste", "dentiste"),
    ("paysag", "paysagiste"),
    ("espaces verts", "paysagiste"),
    ("jardin", "paysagiste"),
    ("fleuri", "fleuriste"),
    ("menuiser", "menuisier"),
    ("serrur", "serrurier"),
    ("couvreu", "couvreur"),
    ("toiture", "couvreur"),
    ("macon", "maçon"),
    ("peintre", "peintre"),
    ("peinture", "peintre"),
    ("carrelage", "carreleur"),
    ("boulanger", "boulanger"),
    ("patisser", "pâtissier"),
    ("boucher", "boucher"),
    ("traiteur", "traiteur"),
    ("pizz", "restaurant"),
    ("restaur", "restaurant"),
)

# Scraper placeholders and words too vague to say "un ___ à Lyon".
_GENERIC: frozenset[str] = frozenset({"entreprise", "etablissement", "inconnu", "commerce", "societe", "professionnel"})
_FALLBACK = "professionnel"


class TradeNormalizer:
    """Resolve a raw business category to a natural French trade noun."""

    @staticmethod
    def _strip_accents(value: str) -> str:
        """Lower-case ``value`` and drop diacritics, for accent-insensitive matching."""
        return TextNormalizer.fold(value)

    @classmethod
    def normalize(cls, category: str | None) -> str:
        """
        Map a scraped category to the trade word a client would use.

        Args:
            category: Raw ``prospect.category`` (free text, may be a placeholder).

        Returns:
            A natural singular trade noun ("garagiste", "plombier", …), the cleaned
            category when it is already usable, or "professionnel" when nothing usable
            remains.
        """
        if not category:
            return _FALLBACK

        ascii_lower = cls._strip_accents(category)
        for keyword, trade in _TRADE_BY_KEYWORD:
            if keyword in ascii_lower:
                return trade

        # No known trade: keep the first segment, lower-cased, so a clean
        # single-word category ("Opticien") still reads naturally in the email.
        first_segment = re.split(r"\s*[,/|]\s*", category.strip(), maxsplit=1)[0].strip()
        cleaned = first_segment.lower()
        if not cleaned or cls._strip_accents(cleaned) in _GENERIC:
            return _FALLBACK
        return cleaned
