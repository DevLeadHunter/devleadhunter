"""
Tests for the fixed service grid: a trade's services are standardised, so barber/mechanic use their
curated default list as-is — every card described, stable count, fake prices stripped — instead of a
scraped-driven grid with empty cards and a variable count. (Food keeps its scraped menu.)
"""

import pytest

from services.templates import registry
from services.templates.barber import BARBER_SERVICES
from services.templates.mechanic_pitlane import MECHANIC_SERVICES


def _services(template_id: str, enrichment: dict) -> list[dict]:
    site = registry.build_site_content(
        template_id=template_id,
        business_name="X",
        phone="0",
        email="x@y.fr",
        city="Tours",
        area="Tours",
        subtitle="",
        palette={"primary": "#000", "secondary": "#111", "accent": "#222"},
        enrichment=enrichment,
    )
    return site["services"]


def test_barber_grid_is_the_fixed_list_regardless_of_scraped() -> None:
    services = _services("barber", {"services": ["Coloration", "Un service random"]})
    assert [s["title"] for s in services] == [s["title"] for s in BARBER_SERVICES]
    assert all(s["description"].strip() for s in services)
    assert all("€" not in s["description"] for s in services)


def test_mechanic_grid_is_the_fixed_list_and_fully_described() -> None:
    services = _services("mechanic-pitlane", {"services": []})
    assert [s["title"] for s in services] == [s["title"] for s in MECHANIC_SERVICES]
    assert all(s["description"].strip() for s in services)


# Every non-food template uses a fixed curated grid: scraped names never leak, no empty cards,
# no fake prices — regardless of what enrichment scraped. (Food keeps its scraped menu.)
_FIXED_GRID_TEMPLATES: list[str] = [
    "barber",
    "mechanic-pitlane",
    "artisan-edito",
    "dental",
    "landscaper-verdure",
    "plumber-signature",
    "plumber-atelier",
    "plumber-cuivre",
    "electrician-lumen",
    "electrician-eclat",
]


@pytest.mark.parametrize("template_id", _FIXED_GRID_TEMPLATES)
def test_non_food_templates_ignore_scraped_services(template_id: str) -> None:
    services = _services(template_id, {"services": ["Un service scrapé bidon", "Autre bidon"]})
    titles = [s["title"] for s in services]
    assert "Un service scrapé bidon" not in titles, f"{template_id} leaked a scraped service"
    assert services, f"{template_id} has no services"
    assert all(s["description"].strip() for s in services), f"{template_id} has an empty card"
    assert all("€" not in s["description"] for s in services), f"{template_id} shows a fake price"
