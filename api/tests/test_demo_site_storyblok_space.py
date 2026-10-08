"""A site generated past Storyblok's daily space limit gets its CMS space later, its content kept (8 Oct 2026)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

import services.demo_site_service as demo_module
from services.demo_site_service import DemoSiteService
from services.storyblok_service import StoryblokProvisionResult, StoryblokService


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
        "business_name": "Exemple Jardins",
        "slug": "exemple-jardins",
        "template_id": "landscaper-verdure",
        "email": "contact@exemple.ch",
        "storyblok_login_email": None,
        "storyblok_space_id": None,
        "content_json": {"about": "Je soigne chaque jardin.", "country": "CH"},
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def provisions(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """The spaces asked of a configured Storyblok, answered with space 42."""
    calls: list[dict[str, Any]] = []

    async def fake_provision(**kwargs: Any) -> StoryblokProvisionResult:
        calls.append(kwargs)
        return StoryblokProvisionResult(
            space_id=42,
            public_token="public",
            preview_token="preview",
            editor_url="https://app.storyblok.com/#/me/spaces/42/dashboard",
            login_email="contact@exemple.ch",
            login_password="secret",
            invite_sent=False,
            content_json={**kwargs["content_json"], "logo": "https://a.storyblok.com/f/42/logo.png"},
            mock_mode=False,
        )

    monkeypatch.setattr(demo_module.storyblok_service, "provision_space_with_content", fake_provision)
    monkeypatch.setattr(StoryblokService, "is_configured", property(lambda self: True))
    monkeypatch.setattr(DemoSiteService, "_prospect_country_for_site", lambda self, db, site: "CH")
    return calls


def test_a_site_without_its_space_gets_one_seeded_from_its_content(provisions: list[dict[str, Any]]) -> None:
    site = _site()

    asyncio.run(DemoSiteService().provision_missing_storyblok_space(_FakeDB(), site))

    assert site.storyblok_space_id == 42
    assert site.content_json["logo"] == "https://a.storyblok.com/f/42/logo.png"
    assert provisions[0]["content_json"] == {"about": "Je soigne chaque jardin.", "country": "CH"}
    assert provisions[0]["country"] == "CH"
    assert provisions[0]["invite_client"] is False


def test_a_site_with_its_space_is_left_alone(provisions: list[dict[str, Any]]) -> None:
    site = _site(storyblok_space_id=7)

    asyncio.run(DemoSiteService().provision_missing_storyblok_space(_FakeDB(), site))

    assert provisions == []
    assert site.storyblok_space_id == 7


def test_a_site_without_content_is_refused(provisions: list[dict[str, Any]]) -> None:
    with pytest.raises(ValueError):
        asyncio.run(DemoSiteService().provision_missing_storyblok_space(_FakeDB(), _site(content_json=None)))
