"""The video's editor demo retypes the site's own hero line, never a trade default with claims the business never made."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.demo_site_service import DemoSiteService
from services.templates import registry


def _site(content_json: object, city: str | None = "Gland") -> SimpleNamespace:
    return SimpleNamespace(template_id="mechanic-pitlane", city=city, content_json=content_json)


def test_the_stored_hero_line_is_retyped() -> None:
    site = _site({"subtitle": " Garage à Gland : entretiens, réparations, préparation à l'expertise. "})

    assert DemoSiteService.hero_line(site) == "Garage à Gland : entretiens, réparations, préparation à l'expertise."


@pytest.mark.parametrize("content_json", [None, {}, {"subtitle": "   "}, {"subtitle": None}])
def test_a_site_without_a_stored_line_falls_back_on_the_trade_default(content_json: object) -> None:
    assert DemoSiteService.hero_line(_site(content_json)) == registry.default_subtitle("mechanic-pitlane", "Gland")


def test_the_default_names_the_area_when_the_city_is_unknown() -> None:
    expected = registry.default_subtitle("mechanic-pitlane", "votre secteur")

    assert DemoSiteService.hero_line(_site(None, city=None)) == expected
