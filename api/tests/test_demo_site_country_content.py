"""A generated site speaks the prospect's regional French: the country travels from the prospect to the content."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

import services.demo_site_service as demo_site_module
from services.demo_site_service import DemoSiteService
from services.storyblok_service import StoryblokService

_PALETTE = {"primary": "#1a4d2e", "secondary": "#f5f1e8", "accent": "#d9a441"}


class _FakeDB:
    def commit(self) -> None:
        return None

    def refresh(self, _row: object) -> None:
        return None


def _site(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 1,
        "user_id": 1,
        "prospect_id": 7,
        "business_name": "Paysagement Tremblay",
        "slug": "paysagement-tremblay",
        "template_id": "landscaper-verdure",
        "phone": "5145550199",
        "email": "info@tremblay.ca",
        "city": "Laval",
        "description": None,
        "content_json": None,
        "image_order": None,
        "image_pool_snapshot": None,
        "section_overrides": None,
        "use_brand_color": True,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _build(country: str) -> str:
    content = StoryblokService().build_content_json(
        business_name="Paysagement Tremblay",
        phone="5145550199",
        email="info@tremblay.ca",
        city="Laval",
        description=None,
        template_id="landscaper-verdure",
        theme=_PALETTE,
        country=country,
    )
    return json.dumps(content, ensure_ascii=False)


def test_a_quebec_site_content_is_written_in_quebec_words() -> None:
    quebec = _build("CA")
    assert "soumission" in quebec.lower()
    assert "devis" not in quebec.lower()
    assert "514 555-0199" in quebec


def test_a_french_site_content_keeps_its_french() -> None:
    france = _build("FR")
    assert "devis" in france.lower()
    assert "soumission" not in france.lower()


def test_the_site_country_is_the_prospect_country(monkeypatch: pytest.MonkeyPatch) -> None:
    service = DemoSiteService()
    monkeypatch.setattr(
        demo_site_module.enrichment_service,
        "get_prospect_for_user",
        lambda _db, _uid, _pid: SimpleNamespace(country="CA"),
    )
    assert service._prospect_country_for_site(_FakeDB(), _site()) == "CA"
    monkeypatch.setattr(demo_site_module.enrichment_service, "get_prospect_for_user", lambda _db, _uid, _pid: None)
    assert service._prospect_country_for_site(_FakeDB(), _site()) == "FR"
    assert service._prospect_country_for_site(_FakeDB(), _site(prospect_id=None)) == "FR"


def test_rebuilding_a_quebec_site_goes_through_the_lexicon(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(DemoSiteService, "_enrichment_dict_for_site", lambda self, db, site: None)
    monkeypatch.setattr(DemoSiteService, "_prospect_country_for_site", lambda self, db, site: "CA")
    content = DemoSiteService()._build_content_for_site_with_theme(_FakeDB(), _site(), theme=_PALETTE)
    dumped = json.dumps(content, ensure_ascii=False).lower()
    assert "soumission" in dumped
    assert "devis" not in dumped


def test_a_new_demo_is_provisioned_in_the_prospect_country(monkeypatch: pytest.MonkeyPatch) -> None:
    """The first content of a demo is built by ``provision_space``: it must read the prospect's country too."""
    seeded: dict[str, str] = {}

    async def _fake_provision_with_content(self: StoryblokService, **kwargs: object) -> str:
        seeded["content"] = json.dumps(kwargs["content_json"], ensure_ascii=False).lower()
        return "provisioned"

    monkeypatch.setattr(StoryblokService, "provision_space_with_content", _fake_provision_with_content)
    result = asyncio.run(
        StoryblokService().provision_space(
            business_name="Paysagement Tremblay",
            slug="paysagement-tremblay",
            phone="5145550199",
            email="info@tremblay.ca",
            city="Laval",
            description=None,
            template_id="landscaper-verdure",
            collaborator_email="",
            preview_url="https://demo.example/paysagement-tremblay",
            theme=_PALETTE,
            country="CA",
        )
    )
    assert result == "provisioned"
    assert "soumission" in seeded["content"]
    assert "devis" not in seeded["content"]
