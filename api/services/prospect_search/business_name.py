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

from services.decision_maker.normalize import company_tokens, join_dotted_initials
from services.prospect_search.trade_catalog import TradeCatalog

_PARENTHESES_RE: re.Pattern[str] = re.compile(r"\([^)]*\)")
# A separator set off by spaces opens a tagline; a hyphen inside a name (« Weiss-Couvreur ») does not.
_TAGLINE_SEPARATOR_RE: re.Pattern[str] = re.compile(r"\s+[-–—|:/·•]+(?:\s+|$)|,\s+")
_SPACES_RE: re.Pattern[str] = re.compile(r"\s+")
_EDGE_PUNCTUATION: str = ' -–—|,;:/·•"«»'
_MINIMUM_NAME_WORDS: int = 2
# Letters, digits, spaces and punctuation make a name; pictographs and trademark signs decorate it.
_NAME_CHARACTER_CATEGORIES: frozenset[str] = frozenset({"L", "N", "Z", "P"})
_KEPT_SYMBOLS: frozenset[str] = frozenset({"+", "|"})
_LEGAL_FORM_RE: re.Pattern[str] = re.compile(
    r"(?<!\w)(s\.?\s?[aà]\.?\s?r\.?\s?l\.?|s\.?\s?a\.?|gmbh|ag|sagl|snc|eurl|sasu?|inc\.?|enr\.?|lt[ée]e)(?!\w)",
    re.IGNORECASE,
)
_MIN_NAME_SIMILARITY: float = 0.5

# Words too common in business names to tell one business from another.
COMMON_NAME_WORDS: frozenset[str] = frozenset(
    {
        "garage",
        "jardin",
        "jardins",
        "paysage",
        "paysages",
        "paysagiste",
        "service",
        "services",
        "entretien",
        "entreprise",
        "automobile",
        "automobiles",
        "plomberie",
        "chauffage",
        "sanitaire",
        "electricite",
        "electricien",
        "atelier",
        "artisan",
        "renovation",
        "travaux",
        "centre",
        "multiservices",
        "amenagement",
        "amenagements",
        "exterieurs",
    }
)

NAME_LINK_WORDS: frozenset[str] = frozenset(
    {
        "du",
        "de",
        "des",
        "la",
        "le",
        "les",
        "et",
        "au",
        "aux",
        "di",
        "da",
        "das",
        "dos",
        "del",
        "von",
        "und",
        "and",
        "the",
        "of",
    }
)
_STEMMED_WORD_MIN_CHARS: int = 5


def _stem(word: str) -> str:
    """A folded word without its plural and feminine endings: « extérieures », « exterieurs » read « exterieur »."""
    if len(word) >= _STEMMED_WORD_MIN_CHARS and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    if len(word) >= _STEMMED_WORD_MIN_CHARS and word.endswith("e") and not word.endswith("ee"):
        word = word[:-1]
    return word


_COMMON_NAME_STEMS: frozenset[str] = frozenset(_stem(word) for word in COMMON_NAME_WORDS)


class BusinessName:
    """Cleans the name a listing gives a business, and tells whether a name is a given business's."""

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
    def without_legal_form(name: str) -> str:
        """The name without its legal form (« Rochat » for « Rochat Sàrl »), or the name itself when nothing else remains."""
        return " ".join(_LEGAL_FORM_RE.sub(" ", name).split()) or name

    @classmethod
    def is_named_like(cls, name: str, business_name: str, *, town: str | None) -> bool:
        """
        Whether a name (a Maps place's, a Facebook page's) is the business's name.

        Only the words that tell a business apart are compared: no legal form, trade word, linking word
        or town, and no tagline (« Exemple Électrique - Maître Électricien Laval »). Most of them must be
        the same (« Exemple & Fils Électricité Générale » is « Exemple Et Fils »). A business named after
        one such word (« Exemple ») matches no name adding a word of its own: « Exemple Électricité » is
        it, « Exemple Jules », a podiatrist, is not; nor is a namesake sharing a first name (« Jules
        Exemple » for « Jules Modèle »). A name saying only a trade and a town (« Garage de Morges »)
        must be the same word for word.

        Args:
            name: The name to check, as the place or page shows it.
            business_name: The prospect's business name.
            town: The prospect's town, if known.

        Returns:
            True when the name is the business's.
        """
        return cls.name_similarity(name, business_name, town=town) is not None

    @classmethod
    def name_similarity(cls, name: str, business_name: str, *, town: str | None) -> float | None:
        """
        The share of distinctive words a name has in common with the business's (see ``is_named_like``).

        Args:
            name: The name to check, as the place or page shows it.
            business_name: The prospect's business name.
            town: The prospect's town, if known.

        Returns:
            The share, from 0.5 to 1, or None when the two names are two businesses'.
        """
        business_distinctive = cls.distinctive_stems(business_name, town=town)
        checked_distinctive = cls.distinctive_stems(cls.clean(name), town=town)
        if not business_distinctive:
            business_words = cls._name_words(business_name)
            return 1.0 if business_words and cls._name_words(cls.clean(name)) == business_words else None
        shared = business_distinctive & checked_distinctive
        similarity = len(shared) / len(business_distinctive | checked_distinctive)
        adds_own_word = bool(checked_distinctive - business_distinctive)
        if similarity < _MIN_NAME_SIMILARITY or (len(business_distinctive) == 1 and adds_own_word):
            return None
        return similarity

    @classmethod
    def is_same_name(cls, name: str, business_name: str) -> bool:
        """
        Whether a name is the business's name word for word, legal form, trade words, accents and dotted initials aside.

        Stricter than ``is_named_like``: a registry company bearing it is the business itself (« MATHIEU EXEMPLE »
        for « Mathieu Exemple Paysagiste »), while « EXEMPLE SERVICES », a cleaning firm, is not « Exemple Services
        Extérieurs », a landscaper.

        Args:
            name: A registry company's name, or one of its trade names.
            business_name: The prospect's business name.

        Returns:
            True when both names have the same words besides their trade.
        """
        business_words = cls._words_beside_trade(business_name)
        return bool(business_words) and cls._words_beside_trade(cls.clean(name)) == business_words

    @classmethod
    def is_exact_name(cls, name: str, business_name: str) -> bool:
        """
        Whether a name is the business's name word for word, its trade words included.

        Stricter than ``is_same_name``: « ABC EXEMPLE & PISCINE » is « ABC Exemple & Piscine », while « SCI DE
        L'EXEMPLE », the landlord, is not « Garage de l'Exemple ».

        Args:
            name: A registry company's name, or one of its trade names.
            business_name: The prospect's business name.

        Returns:
            True when both names have the same words, legal form, accents and dotted initials aside.
        """
        business_stems = {_stem(word) for word in cls._name_words(business_name)}
        return bool(business_stems) and {_stem(word) for word in cls._name_words(cls.clean(name))} == business_stems

    @classmethod
    def _words_beside_trade(cls, name: str) -> set[str]:
        """The stems of a name's words without its legal form and its trade words."""
        return {_stem(word) for word in cls._name_words(name) if not TradeCatalog.is_trade_word(word)}

    @classmethod
    def distinctive_words(cls, name: str, *, town: str | None = None) -> set[str]:
        """
        The words of a name that tell its business from another: no legal form, trade word, common or linking word, nor town.

        Args:
            name: A business name.
            town: The business's town, if known.

        Returns:
            The distinctive words, folded (« Exemple & Fils Électricité » gives « exemple », « fils »).
        """
        return cls._distinctive(cls._name_words(name)) - company_tokens(town or "")

    @classmethod
    def distinctive_stems(cls, name: str, *, town: str | None = None) -> set[str]:
        """
        The distinctive words of a name without their plural and feminine endings, to compare two spellings.

        Args:
            name: A business name.
            town: The business's town, if known.

        Returns:
            The stems (« Arbres aux paysages Exemple » gives « arbr », « exemple »).
        """
        return {_stem(word) for word in cls.distinctive_words(name, town=town)}

    @classmethod
    def _name_words(cls, name: str) -> set[str]:
        """The words of a name, its legal form left out (« inc », « Sàrl ») and its dotted initials joined."""
        return company_tokens(join_dotted_initials(cls.without_legal_form(name)))

    @staticmethod
    def _distinctive(words: set[str]) -> set[str]:
        """The words that tell a business from another: no trade word, no word common to many names, no link word."""
        return {
            word
            for word in words
            if word not in COMMON_NAME_WORDS
            and _stem(word) not in _COMMON_NAME_STEMS
            and word not in NAME_LINK_WORDS
            and not TradeCatalog.is_trade_word(word)
        }

    @staticmethod
    def _without_decoration(name: str) -> str:
        """Drop pictographs, trademark signs and invisible joiners; each leaves a space."""
        return "".join(
            character
            if unicodedata.category(character)[0] in _NAME_CHARACTER_CATEGORIES or character in _KEPT_SYMBOLS
            else " "
            for character in name
        )
