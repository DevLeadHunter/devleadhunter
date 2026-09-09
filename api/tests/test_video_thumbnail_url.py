"""The email thumbnail URL changes with each video generation, so a regenerated thumbnail is never served from cache."""

from datetime import UTC, datetime

import pytest

import services.demo_video_service as video_module
from services.demo_video_service import public_thumbnail_url


def test_thumbnail_url_carries_the_generation_instant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(video_module.r2_storage, "public_url", lambda key: f"https://cdn/{key}")
    monkeypatch.setattr(video_module.r2_storage, "website_thumbnail_key", lambda slug: f"videos/{slug}/thumb.jpg")
    generated_at = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    assert public_thumbnail_url("sapori") == "https://cdn/videos/sapori/thumb.jpg"
    assert (
        public_thumbnail_url("sapori", generated_at)
        == f"https://cdn/videos/sapori/thumb.jpg?v={int(generated_at.timestamp())}"
    )
