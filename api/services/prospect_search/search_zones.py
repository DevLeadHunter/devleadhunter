"""
Search zones — the towns a search walks through when the user names none.

Each country has a list of towns big enough to return local results and small enough
for independent tradespeople to be found. A search starts at a different town each
time and leaves for later the towns it already scanned for the same trade.
"""

from __future__ import annotations

import random

from services.decision_maker.normalize import fold

# Brittany is left out on purpose: the towns closest to the user are kept for later.
_TOWNS_BY_COUNTRY: dict[str, tuple[str, ...]] = {
    "FR": (
        "Limoges",
        "Clermont-Ferrand",
        "Dijon",
        "Besançon",
        "Nancy",
        "Metz",
        "Reims",
        "Amiens",
        "Orléans",
        "Tours",
        "Poitiers",
        "Angers",
        "Le Mans",
        "Caen",
        "Rouen",
        "Troyes",
        "Bourges",
        "Châteauroux",
        "Nevers",
        "Auxerre",
        "Chalon-sur-Saône",
        "Mâcon",
        "Roanne",
        "Saint-Étienne",
        "Valence",
        "Avignon",
        "Nîmes",
        "Béziers",
        "Perpignan",
        "Narbonne",
        "Carcassonne",
        "Albi",
        "Montauban",
        "Agen",
        "Périgueux",
        "Brive-la-Gaillarde",
        "Angoulême",
        "La Rochelle",
        "Niort",
        "Pau",
        "Tarbes",
        "Mont-de-Marsan",
        "Aurillac",
        "Le Puy-en-Velay",
        "Annecy",
        "Chambéry",
        "Gap",
        "Épinal",
        "Colmar",
        "Mulhouse",
        "Belfort",
        "Charleville-Mézières",
        "Saint-Quentin",
        "Beauvais",
        "Chartres",
        "Blois",
        "Cholet",
        "La Roche-sur-Yon",
        "Alès",
        "Arles",
        "Draguignan",
        "Montluçon",
        "Vichy",
        "Bergerac",
        "Dax",
        "Rodez",
        "Cahors",
        "Saintes",
        "Châtellerault",
        "Vierzon",
    ),
    "CH": (
        "Lausanne",
        "Genève",
        "Fribourg",
        "Neuchâtel",
        "Sion",
        "Yverdon-les-Bains",
        "Montreux",
        "La Chaux-de-Fonds",
        "Vevey",
        "Nyon",
        "Martigny",
        "Bulle",
        "Morges",
        "Delémont",
        "Monthey",
        "Sierre",
        "Aigle",
        "Payerne",
        "Porrentruy",
        "Bienne",
    ),
    "CA": (
        "Montréal",
        "Laval",
        "Longueuil",
        "Terrebonne",
        "Québec",
        "Gatineau",
        "Sherbrooke",
        "Trois-Rivières",
        "Lévis",
        "Saguenay",
        "Drummondville",
        "Saint-Jérôme",
        "Granby",
        "Saint-Hyacinthe",
        "Repentigny",
        "Blainville",
        "Victoriaville",
        "Rimouski",
        "Shawinigan",
        "Joliette",
        "Saint-Jean-sur-Richelieu",
    ),
    "BE": (
        "Liège",
        "Charleroi",
        "Namur",
        "Mons",
        "Tournai",
        "La Louvière",
        "Verviers",
        "Mouscron",
        "Wavre",
        "Nivelles",
        "Arlon",
        "Huy",
        "Dinant",
        "Bastogne",
        "Ath",
        "Bruxelles",
    ),
    "LU": ("Luxembourg", "Esch-sur-Alzette", "Differdange", "Dudelange", "Ettelbruck", "Diekirch"),
}


class SearchZones:
    """Chooses the towns a search goes through."""

    @staticmethod
    def towns_of(country: str) -> tuple[str, ...]:
        """Default towns of a country (the French ones for an unknown country)."""
        return _TOWNS_BY_COUNTRY.get(country.upper(), _TOWNS_BY_COUNTRY["FR"])

    @classmethod
    def plan(
        cls,
        *,
        country: str,
        asked_cities: list[str],
        already_scanned: set[str],
        seed: int,
    ) -> list[str]:
        """
        Order the towns of a search.

        Args:
            country: ISO code of the search country.
            asked_cities: Towns typed by the user; when given, only those are searched, in that order.
            already_scanned: Towns earlier searches scanned for the same trade (folded names).
            seed: Makes the order differ from one search to the next, and stay the same on resume.

        Returns:
            The towns to search, fresh ones first.
        """
        cleaned = [city.strip() for city in asked_cities if city and city.strip()]
        if cleaned:
            return cleaned
        towns = list(cls.towns_of(country))
        random.Random(seed).shuffle(towns)
        fresh = [town for town in towns if fold(town) not in already_scanned]
        scanned = [town for town in towns if fold(town) in already_scanned]
        return fresh + scanned
