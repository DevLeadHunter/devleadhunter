"""Unit tests for the Réceptionniste IA target verticals.

Scraped categories are free text that differs per source (Google label, Pages
Jaunes activities, OSM tag), so the catalog must recognize a vertical from any of
its usual spellings and stay silent on the trades it does not target.
"""

import asyncio

import pytest

from api.v1.routes.sources import get_sourcing_verticals
from services.sourcing_verticals import SourcingVerticalCatalog


@pytest.mark.parametrize(
    ("category", "expected_key"),
    [
        ("Couvreur", "couvreur"),
        ("COUVREUR ZINGUEUR", "couvreur"),
        ("Entreprise de toiture", "couvreur"),
        ("Charpentier", "charpentier"),
        ("Atelier de carrosserie", "carrosserie"),
        ("Carrossier", "carrosserie"),
        ("Salle de réception", "lieu-mariage"),
        ("Lieu de mariage", "lieu-mariage"),
        ("Traiteur", "traiteur"),
        ("Agence immobilière", "agence-immobiliere"),
        ("Agent immobilier", "agence-immobiliere"),
    ],
)
def test_categories_are_matched_to_their_vertical(category: str, expected_key: str) -> None:
    vertical = SourcingVerticalCatalog.match(category)

    assert vertical is not None
    assert vertical.key == expected_key


@pytest.mark.parametrize("category", [None, "", "Plombier", "Coiffeur", "Entreprise", "Restaurant"])
def test_non_target_categories_match_nothing(category: str | None) -> None:
    assert SourcingVerticalCatalog.match(category) is None


def test_catalog_keys_are_unique_and_waves_start_at_one() -> None:
    keys = [vertical.key for vertical in SourcingVerticalCatalog.VERTICALS]
    waves = [vertical.wave for vertical in SourcingVerticalCatalog.VERTICALS]

    assert len(keys) == len(set(keys))
    assert min(waves) == 1
    assert waves == sorted(waves)


def test_every_search_term_is_recognized_by_its_own_vertical() -> None:
    for vertical in SourcingVerticalCatalog.VERTICALS:
        assert vertical.search_terms
        for term in vertical.search_terms:
            assert SourcingVerticalCatalog.match(term) == vertical


def test_verticals_endpoint_lists_the_catalog_in_order() -> None:
    verticals = asyncio.run(get_sourcing_verticals())

    assert [vertical.key for vertical in verticals] == [v.key for v in SourcingVerticalCatalog.VERTICALS]
    assert verticals[0].wave == 1
    assert verticals[0].search_terms == ["Couvreur"]
