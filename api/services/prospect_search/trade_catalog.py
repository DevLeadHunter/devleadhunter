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
    is_generic: bool = field(default=False)

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
        category_keywords=("paysag", "jardin", "pelouse", "elag", "espaces verts", "arbre", "amenagement exterieur"),
        excluded_category_keywords=(*_SHOP_CATEGORIES, "architecte", "jardinerie", "centre de jardinage", "fleuriste"),
    ),
    TradeProfile(
        key="electricien",
        label="Électricien",
        prospect_category="électricien",
        aliases=("electricien", "electriciens", "electricite", "electricite generale"),
        search_terms={_DEFAULT_COUNTRY: ("électricien",), "CA": ("électricien", "entrepreneur électricien")},
        category_keywords=("electri",),
        excluded_category_keywords=(*_SHOP_CATEGORIES, "fournisseur d'electricite", "compagnie d'electricite"),
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
        ),
        excluded_category_keywords=(
            *_SHOP_CATEGORIES,
            "concessionnaire",
            "location",
            "pieces",
            "lavage",
            "porte",
            "door",
            "controle technique",
            "parking",
            "station-service",
            "porte de garage",
        ),
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
