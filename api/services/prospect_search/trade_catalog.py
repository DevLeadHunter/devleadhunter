"""
Trade catalog — how each trade is searched and recognised, country by country.

A trade typed by the user (« Électricien », « sanitaire-chauffage ») resolves to a
profile: the words to search in each country, the Google categories that confirm the
trade and the ones that deny it, and the public registries that list it. An unknown
trade gets a generic profile built from the typed words.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from services.decision_maker.normalize import fold

_DEFAULT_COUNTRY: str = "*"
_NAME_WORD_SEPARATORS_RE: re.Pattern[str] = re.compile(r"[^a-z0-9]+")
# Words a dealer's name may start with before its brand (« Garage Renault Exemple », « Ets Peugeot »).
_LEADING_DEALER_WORDS: frozenset[str] = frozenset(
    {"garage", "garages", "agence", "agent", "concession", "concessionnaire", "ets", "etablissements", "sarl", "sas"}
)
# Words naming a brand's outlet wherever they stand (« Garage Exemple Agent Renault »).
_DEALER_WORDS: tuple[str, ...] = ("agent", "concession", "concessionnaire", "distributeur", "reparateur agree")
_DEALER_CATEGORY_WORD: str = "concessionnaire"
_SHORT_BRAND_MAX_CHARS: int = 3
# Crafts a business name may say (« La petite Maçonnerie », « Exemple Chauffagiste »): the craft, seldom the
# craftsman, whose word is often a family name (« Barbier », « Couvreur »).
_CRAFT_NAME_WORDS: frozenset[str] = frozenset(
    {
        "maconnerie",
        "plomberie",
        "chauffage",
        "chauffagiste",
        "electricite",
        "menuiserie",
        "ebenisterie",
        "toiture",
        "couverture",
        "zinguerie",
        "charpente",
        "carrelage",
        "peinture",
        "platrerie",
        "serrurerie",
        "vitrerie",
        "carrosserie",
        "mecanique",
        "garage",
        "coiffure",
        "restaurant",
        "boulangerie",
        "boucherie",
        "pizzeria",
        "traiteur",
    }
)


@dataclass(frozen=True)
class TradeProfile:
    """Search and recognition rules of one trade."""

    key: str
    label: str
    prospect_category: str
    aliases: tuple[str, ...]
    search_terms: dict[str, tuple[str, ...]]
    category_keywords: tuple[str, ...]
    excluded_category_keywords: tuple[str, ...] = ()
    rge_domains: tuple[str, ...] = ()
    rbq_subcategories: tuple[str, ...] = ()
    brand_names: tuple[str, ...] = ()
    brands_named_by_category_only: tuple[str, ...] = ()
    is_generic: bool = field(default=False)

    def names_trade(self, name: str) -> bool:
        """Whether a business name says the trade (« Rochat Électricité », « Jardins du Lac »)."""
        folded_name = fold(name)
        return any(fold(word) in folded_name for word in (*self.aliases, *self.category_keywords))

    def names_another_trade(self, name: str) -> bool:
        """
        Whether a business name says another trade and not this one (« La petite Maçonnerie » for a landscaper).

        A name saying both trades (« Électricité Chauffage Exemple ») is this trade's.

        Args:
            name: The business name, as the listing writes it.

        Returns:
            True when one of its words names another trade and none names this one.
        """
        own_words = {fold(word) for word in self.aliases}
        name_words = set(_NAME_WORD_SEPARATORS_RE.split(fold(name)))
        return bool(name_words & (_CRAFT_NAME_WORDS - own_words)) and not self.names_trade(name)

    def brand_outlet_of(self, name: str, google_category: str | None) -> str | None:
        """
        The brand a business is the agent or the dealer of, as its listing shows it.

        A brand heads its name (« Peugeot - Garage Exemple », « Renault / Dacia - Garage Exemple »), follows
        « agent » or « concession » in it, or names its category (« Concessionnaire Peugeot »); a dealer's
        category without a brand (« Concessionnaire automobile ») counts with a brand anywhere in the name
        (« Garage Exemple voitures sans permis Aixam »). A brand whose name is a common word (« Mini »)
        counts only in the category. Its owner does not decide on a website alone.

        Args:
            name: The business name, as the listing writes it.
            google_category: Its Google category, if known.

        Returns:
            The brand, written for a reader (« Peugeot », « BMW »), or None for an independent business.
        """
        name_words = f" {_NAME_WORD_SEPARATORS_RE.sub(' ', fold(name)).strip()} "
        words = name_words.split()
        while words and words[0] in _LEADING_DEALER_WORDS:
            words.pop(0)
        head = f" {' '.join(words)} "
        category = _NAME_WORD_SEPARATORS_RE.sub(" ", fold(google_category or "")).strip()
        for brand in (*self.brand_names, *self.brands_named_by_category_only):
            is_brand_category = f"{category} ".startswith(f"{_DEALER_CATEGORY_WORD} {brand} ")
            is_named_brand = brand in self.brand_names and (
                head.startswith(f" {brand} ")
                or any(f" {word} {brand} " in name_words for word in _DEALER_WORDS)
                or (category.startswith(_DEALER_CATEGORY_WORD) and f" {brand} " in name_words)
            )
            if is_brand_category or is_named_brand:
                return brand.upper() if len(brand) <= _SHORT_BRAND_MAX_CHARS else brand.title()
        return None

    def terms_for(self, country: str) -> tuple[str, ...]:
        """Search words of the trade in a country (the default words when none are specific)."""
        return self.search_terms.get(country.upper()) or self.search_terms[_DEFAULT_COUNTRY]

    def accepts_category(self, google_category: str | None) -> bool:
        """
        Whether a Google category fits the trade.

        An empty category is accepted (the verification decides later); a generic
        profile accepts everything that is not explicitly excluded.
        """
        if not google_category:
            return True
        category = fold(google_category)
        if any(fold(keyword) in category for keyword in self.excluded_category_keywords):
            return False
        if self.is_generic:
            return True
        return any(fold(keyword) in category for keyword in self.category_keywords)


_SHOP_CATEGORIES: tuple[str, ...] = ("magasin", "fournisseur", "grossiste", "ecole", "formation", "association")

_PROFILES: tuple[TradeProfile, ...] = (
    TradeProfile(
        key="paysagiste",
        label="Paysagiste",
        prospect_category="paysagiste",
        aliases=("paysagiste", "paysagistes", "jardinier", "jardinier paysagiste", "entretien de jardin"),
        search_terms={
            _DEFAULT_COUNTRY: ("paysagiste", "entretien de jardin"),
            "CA": ("paysagiste", "entretien paysager"),
        },
        category_keywords=(
            "paysag",
            "jardin",
            "pelouse",
            "tonte",
            "elag",
            "debroussaill",
            "espaces verts",
            "arbre",
            "amenagement exterieur",
            "clotur",
            "arrosage",
            "irrigation",
        ),
        excluded_category_keywords=(
            *_SHOP_CATEGORIES,
            "architecte",
            "jardinerie",
            "centre de jardinage",
            "fleuriste",
            "jardin d'enfants",
            "jardin botanique",
            "jardin public",
            "jardin zoologique",
            "creche",
        ),
    ),
    TradeProfile(
        key="electricien",
        label="Électricien",
        prospect_category="électricien",
        aliases=("electricien", "electriciens", "electricite", "electricite generale", "elec"),
        search_terms={_DEFAULT_COUNTRY: ("électricien",), "CA": ("électricien", "entrepreneur électricien")},
        category_keywords=("electri", "domotique", "eclairage"),
        excluded_category_keywords=(
            *_SHOP_CATEGORIES,
            "fournisseur d'electricite",
            "compagnie d'electricite",
            "centrale",
            "hydroelectrique",
            "station electrique",
            "sous-station",
            "power plant",
            "power station",
            "substation",
            "recharge",
            "appareil",
        ),
        rge_domains=("Radiateurs électriques, dont régulation.",),
        rbq_subcategories=("16",),
    ),
    TradeProfile(
        key="plombier",
        label="Plombier-chauffagiste",
        prospect_category="plombier",
        aliases=(
            "plombier",
            "plombiers",
            "plomberie",
            "plombier chauffagiste",
            "chauffagiste",
            "sanitaire chauffage",
            "sanitaire-chauffage",
            "installateur sanitaire",
        ),
        search_terms={
            _DEFAULT_COUNTRY: ("plombier chauffagiste", "plombier"),
            "CH": ("installateur sanitaire", "sanitaire chauffage"),
            "CA": ("plombier", "plomberie chauffage"),
        },
        category_keywords=("plomb", "chauffag", "sanitaire", "installation de chauffage"),
        excluded_category_keywords=_SHOP_CATEGORIES,
        rge_domains=(
            "Chaudière condensation ou micro-cogénération gaz ou fioul",
            "Pompe à chaleur : chauffage",
            "Chauffe-Eau Thermodynamique",
            "Chauffage et/ou eau chaude solaire",
        ),
        rbq_subcategories=("15.5", "15.1", "15.2", "15.3", "15.4"),
    ),
    TradeProfile(
        key="garage",
        label="Garage automobile",
        prospect_category="garage automobile",
        aliases=("garage", "garagiste", "garage automobile", "mecanicien", "mecanique automobile", "garage auto"),
        search_terms={
            _DEFAULT_COUNTRY: ("garage automobile",),
            "CA": ("garage mécanique automobile", "atelier mécanique"),
        },
        category_keywords=(
            "garage",
            "reparation automobile",
            "mecani",
            "atelier de reparation",
            "entretien automobile",
            "carross",
            "jante",
            "pneu",
            "pare-brise",
            "concessionnaire",
            "voiture",
            "vehicule",
            "moto",
            "remorqu",
            "depanneuse",
        ),
        excluded_category_keywords=(
            *_SHOP_CATEGORIES,
            "location",
            "pieces",
            "lavage",
            "porte",
            "door",
            "controle technique",
            "parking",
            "station-service",
            "porte de garage",
            "assurance",
            "expert",
            "fourriere",
            "recharge",
        ),
        brand_names=(
            "abarth",
            "aixam",
            "alfa romeo",
            "aston martin",
            "audi",
            "bentley",
            "bmw",
            "byd",
            "chatenet",
            "chevrolet",
            "chrysler",
            "citroen",
            "cupra",
            "dacia",
            "dodge",
            "ducati",
            "ferrari",
            "fiat",
            "ford",
            "harley davidson",
            "honda",
            "hyundai",
            "infiniti",
            "isuzu",
            "iveco",
            "jaguar",
            "jeep",
            "kawasaki",
            "kia",
            "lamborghini",
            "lancia",
            "land rover",
            "lexus",
            "ligier",
            "maserati",
            "mazda",
            "mercedes",
            "microcar",
            "mitsubishi",
            "nissan",
            "opel",
            "peugeot",
            "piaggio",
            "porsche",
            "renault",
            "seat",
            "skoda",
            "ssangyong",
            "subaru",
            "suzuki",
            "tesla",
            "toyota",
            "triumph",
            "volkswagen",
            "volvo",
            "vw",
            "yamaha",
        ),
        # Brands named like common words (« Mini », « Smart »): only Google's category tells their dealers.
        brands_named_by_category_only=("alpine", "ds", "lotus", "mg", "mini", "smart"),
    ),
    TradeProfile(
        key="couvreur",
        label="Couvreur",
        prospect_category="couvreur",
        aliases=("couvreur", "couvreurs", "couverture", "toiture", "couvreur zingueur"),
        search_terms={_DEFAULT_COUNTRY: ("couvreur",), "CA": ("couvreur", "entrepreneur en toiture")},
        category_keywords=("couvr", "toit", "zingu", "charpent"),
        excluded_category_keywords=_SHOP_CATEGORIES,
    ),
    TradeProfile(
        key="menuisier",
        label="Menuisier",
        prospect_category="menuisier",
        aliases=("menuisier", "menuisiers", "menuiserie", "ebeniste"),
        search_terms={_DEFAULT_COUNTRY: ("menuisier",)},
        category_keywords=("menuis", "ebenist", "charpent"),
        excluded_category_keywords=_SHOP_CATEGORIES,
    ),
    TradeProfile(
        key="barbier",
        label="Barbier",
        prospect_category="barbier",
        aliases=("barbier", "barbiers", "barber", "barbershop", "coiffeur barbier"),
        search_terms={_DEFAULT_COUNTRY: ("barbier",)},
        category_keywords=("barb", "coiff"),
        excluded_category_keywords=("ecole", "formation", "fournisseur"),
    ),
    TradeProfile(
        key="food-truck",
        label="Food truck",
        prospect_category="food truck",
        aliases=("food truck", "foodtruck", "camion restaurant", "cantine mobile"),
        search_terms={_DEFAULT_COUNTRY: ("food truck",), "CA": ("camion de cuisine de rue", "food truck")},
        category_keywords=("food truck", "restaura", "traiteur", "snack", "pizz", "burger", "cuisine"),
    ),
)


class TradeCatalog:
    """Resolves a typed trade to its search and recognition profile."""

    @classmethod
    def profiles(cls) -> tuple[TradeProfile, ...]:
        """Every trade the catalog describes."""
        return _PROFILES

    @classmethod
    def is_trade_word(cls, word: str) -> bool:
        """Whether a word of a business name says a trade the catalog knows (« électrique », « paysagiste »)."""
        folded_word = fold(word)
        return any(
            folded_word.startswith(keyword)
            for profile in _PROFILES
            for keyword in (*profile.category_keywords, *profile.aliases)
            if " " not in keyword
        )

    @classmethod
    def resolve(cls, typed_trade: str) -> TradeProfile:
        """
        Find the profile of a trade typed by the user.

        Args:
            typed_trade: Free text (« Électricien », « sanitaire-chauffage »…).

        Returns:
            The catalog profile, or a generic one searching the typed words as they are.
        """
        typed = re.sub(r"\s+", " ", fold(typed_trade).replace("-", " ")).strip()
        for profile in _PROFILES:
            if typed == profile.key or typed in {fold(alias).replace("-", " ") for alias in profile.aliases}:
                return profile
        cleaned = typed_trade.strip()
        return TradeProfile(
            key=typed.replace(" ", "-") or "metier",
            label=cleaned[:1].upper() + cleaned[1:],
            prospect_category=cleaned.lower(),
            aliases=(typed,),
            search_terms={_DEFAULT_COUNTRY: (cleaned,)},
            category_keywords=tuple(token for token in typed.split(" ") if len(token) > 3),
            excluded_category_keywords=("ecole", "formation"),
            is_generic=True,
        )
