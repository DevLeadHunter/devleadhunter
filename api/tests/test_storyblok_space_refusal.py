"""A space Storyblok refuses must leave the new site live from its content (1 Nov 2026).

Past Storyblok's daily limit, creating a space answers 429. The batch of wave 5 then got « failed » shells, which no
outreach sends and the missing-space pass never picks up. A refused space is a provisioning error without a space:
the site renders from ``content_json`` and gets its space later.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from services.storyblok_service import StoryblokProvisionError, StoryblokService

_SPACES_URL: str = "https://mapi.storyblok.com/v1/spaces/"


class _RefusingClient:
    """A Storyblok that has created its spaces for the day."""

    async def __aenter__(self) -> _RefusingClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def post(self, url: str, **_kwargs: object) -> httpx.Response:
        return httpx.Response(
            429, json={"error": "Sorry you hit a rate limit"}, request=httpx.Request("POST", url or _SPACES_URL)
        )


def test_a_refused_space_is_a_provisioning_error_without_a_space(monkeypatch: pytest.MonkeyPatch) -> None:
    service = StoryblokService()
    monkeypatch.setattr(StoryblokService, "is_configured", property(lambda self: True))
    monkeypatch.setattr("services.storyblok_service.httpx.AsyncClient", lambda **_kwargs: _RefusingClient())
    content: dict[str, Any] = {"businessName": "Garage Bel Air"}

    with pytest.raises(StoryblokProvisionError) as refusal:
        asyncio.run(
            service.provision_space_with_content(
                business_name="Garage Bel Air",
                slug="garage-bel-air",
                template_id="mechanic-pitlane",
                collaborator_email="",
                preview_url="https://demo.example.com/garage-bel-air",
                content_json=content,
            )
        )

    assert refusal.value.space_id is None
    assert refusal.value.content_json == content
    assert "429" in str(refusal.value)
