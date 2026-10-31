"""Where a French address, number or prospect sits: mainland France or one of the overseas departments."""

from types import SimpleNamespace

from scrappers.google_scraper import GoogleScraper
from services.french_overseas import FrenchOverseas

MARTINIQUE = FrenchOverseas.by_code("MQ")


def test_an_address_is_placed_by_its_postal_code_whatever_the_order_google_writes() -> None:
    assert FrenchOverseas.of_address("Zi la Lézarde, Le Lamentin 97232, Martinique") is MARTINIQUE
    assert FrenchOverseas.of_address("Lot. 97 Les Hauts, 97200 Fort-de-France") is MARTINIQUE
    assert FrenchOverseas.of_address("12 Rue de la Réunion, 75020 Paris") is None


def test_an_address_without_postal_code_is_placed_by_the_department_named_at_its_end() -> None:
    assert FrenchOverseas.of_address("35 Imp. Jacinthe, Le Lamentin, Martinique") is MARTINIQUE
    reunion = FrenchOverseas.of_address("Chemin Bœuf Mort, Saint-Pierre, La Réunion")
    assert reunion is not None and reunion.code == "RE"
    assert FrenchOverseas.of_address("12 Rue de la Réunion") is None


def test_reunion_and_mayotte_share_a_dial_code_not_their_numbers() -> None:
    assert FrenchOverseas.of_e164("+262692123456").label == "La Réunion"
    assert FrenchOverseas.of_e164("+262639123456").label == "Mayotte"
    assert FrenchOverseas.of_e164("+33612345678") is None


def test_a_prospect_is_placed_by_his_address_before_his_numbers() -> None:
    by_address = SimpleNamespace(country="FR", address="Le Robert 97231, Martinique", phones=[], phone=None)
    by_number = SimpleNamespace(country="FR", address="", phones=["+596 596 50 58 09"], phone="+596 596 50 58 09")
    mainland = SimpleNamespace(country="FR", address="41000 Blois", phones=["0696 04 04 25"], phone="0696 04 04 25")
    swiss = SimpleNamespace(country="CH", address="Le Robert 97231, Martinique", phones=[], phone=None)

    assert FrenchOverseas.of_prospect(by_address) is MARTINIQUE
    assert FrenchOverseas.of_prospect(by_number) is MARTINIQUE
    assert FrenchOverseas.of_prospect(mainland) is None
    assert FrenchOverseas.of_prospect(swiss) is None


def test_the_commune_an_address_names_is_the_last_one_written() -> None:
    assert MARTINIQUE.commune_in("Route De Jeanne D'Arc LE LAMENTIN, 97232, Martinique") == "Le Lamentin"
    assert MARTINIQUE.commune_in("Route de Sainte-Marie, 97220 La Trinité, Martinique") == "La Trinité"
    assert MARTINIQUE.commune_in("Rue Victor Hugo, 97233 SCHOELCHER") == "Schœlcher"
    assert MARTINIQUE.commune_in("Route du Lamentin, 97200 Fort-de-France") == "Fort-de-France"
    assert MARTINIQUE.commune_in("12 Rue Nationale, 41000 Blois") is None


def test_a_martinique_address_gives_its_commune_as_the_city() -> None:
    assert GoogleScraper.extract_city("Route De Jeanne D'Arc LE LAMENTIN, 97232, Martinique", "FR") == "Le Lamentin"
    assert GoogleScraper.extract_city("35 Imp. Jacinthe, Le Lamentin, Martinique", "FR") == "Le Lamentin"
    assert GoogleScraper.extract_city("12 Rue Nationale, 41000 Blois", "FR") == "Blois"


def test_only_martinique_is_open_to_the_search_and_its_biggest_communes_come_first() -> None:
    assert [department.code for department in FrenchOverseas.searchable()] == ["MQ"]
    assert MARTINIQUE.communes[:4] == ("Fort-de-France", "Le Lamentin", "Le Robert", "Schœlcher")
    assert len(MARTINIQUE.communes) == len(set(MARTINIQUE.communes)) == 34
