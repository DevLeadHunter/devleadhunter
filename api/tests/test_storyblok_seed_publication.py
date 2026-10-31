"""A space seeded from the site's own content must not sync that publication back into the site (31 Oct 2026).

The publish webhook rewrites ``content_json`` from the story's blocks: seeding the space of a site that gets one back
would have changed the photos' hosts and dropped what the blocks cannot hold (the legacy garage FAQ photo), so the
site moved. With ``sync_seed_publication=False`` the webhook only starts listening once the story is published.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from services.storyblok_service import StoryblokService


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _Client:
    """A Storyblok that creates space 5 and describes it."""

    async def __aenter__(self) -> _Client:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def post(self, _url: str, **_kwargs: object) -> _Response:
        return _Response({"space": {"id": 5}})

    async def get(self, _url: str, **_kwargs: object) -> _Response:
        return _Response({"space": {"first_token": "public", "preview_token": "preview"}})


def _provision(monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> list[str]:
    """Run a provisioning and return the order of the steps it took."""
    steps: list[str] = []

    async def step(name: str) -> None:
        steps.append(name)

    service = StoryblokService()
    monkeypatch.setattr(StoryblokService, "is_configured", property(lambda self: True))
    monkeypatch.setattr("services.storyblok_service.httpx.AsyncClient", lambda **_kwargs: _Client())
    monkeypatch.setattr(service, "_configure_preview_url", lambda *_args: step("preview url"))
    monkeypatch.setattr(service, "_ensure_template_components", lambda *_args: step("components"))
    monkeypatch.setattr(service, "_register_publish_webhook", lambda *_args: step("webhook"))
    monkeypatch.setattr(service, "_publish_home_story", lambda *_args, **_kwargs: step("seed story"))

    result = asyncio.run(
        service.provision_space_with_content(
            business_name="TP Motorsport",
            slug="tp-motorsport",
            template_id="mechanic-pitlane",
            collaborator_email="",
            preview_url="https://demo.example.com/tp-motorsport",
            content_json={"businessName": "TP Motorsport"},
            **kwargs,
        )
    )

    assert result.space_id == 5
    assert result.content_json == {"businessName": "TP Motorsport"}
    return steps


def test_the_webhook_listens_only_after_the_story_is_seeded_when_the_seed_is_not_synced_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    steps = _provision(monkeypatch, sync_seed_publication=False)

    assert steps[-1] == "webhook"
    assert steps.index("seed story") < steps.index("webhook")
    assert sorted(steps[:2]) == ["components", "preview url"]


def test_the_webhook_is_registered_before_the_seed_by_default_as_for_a_new_site(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    steps = _provision(monkeypatch)

    assert steps[-1] == "seed story"
    assert steps.index("webhook") < steps.index("seed story")
