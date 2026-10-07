"""
How the Google photo grid is opened and read (first enrichment round, 7 Oct 2026): logged out, the hero
viewer stops at about ten photos, or opens Street View, while the « Photos » section's grid lists them all
(31 against 10 on a Swiss landscaper).
"""

import asyncio
from typing import Any

import pytest

from scrappers import enrichment_scraper as scraper_module
from scrappers.enrichment_scraper import (
    _OPEN_PHOTO_COUNT_JS,
    _OPEN_PHOTOS_JS,
    EnrichmentScraper,
)


@pytest.fixture(autouse=True)
def instant_page(monkeypatch: pytest.MonkeyPatch) -> None:
    """No real browser: scrolling and waiting do nothing."""

    async def evaluate(tab: Any, js: str, *, by_value: bool = True, await_promise: bool = False) -> Any:
        return None

    async def no_wait(seconds: float) -> None:
        return None

    monkeypatch.setattr(scraper_module.NodriverDom, "evaluate", evaluate)
    monkeypatch.setattr(scraper_module.asyncio, "sleep", no_wait)


def _scraper_opening(monkeypatch: pytest.MonkeyPatch, *, opens: dict[str, int]) -> tuple[EnrichmentScraper, list[str]]:
    """A scraper whose openers work as scripted: the category from its n-th try, the count or the hero at once."""
    scraper = EnrichmentScraper()
    tries: list[str] = []

    async def opens_grid(tab: Any, script: str) -> bool:
        name = "count" if script == _OPEN_PHOTO_COUNT_JS else "hero" if script == _OPEN_PHOTOS_JS else "category"
        tries.append(name)
        return name in opens and tries.count(name) >= opens[name]

    monkeypatch.setattr(scraper, "_opens_grid", opens_grid)
    return scraper, tries


def test_the_photos_section_is_scrolled_to_before_the_hero(monkeypatch: pytest.MonkeyPatch) -> None:
    """The category chips render once scrolled to: the capped hero is never tried first."""
    scraper, tries = _scraper_opening(monkeypatch, opens={"category": 3, "hero": 1})

    opener = asyncio.run(scraper._open_photo_grid(object(), place_url=None, place_title=None))

    assert opener == "category"
    assert "hero" not in tries


def test_the_plain_layout_opens_from_its_photo_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without category chips, the section's « 32 photos » opens the grid before the hero."""
    scraper, tries = _scraper_opening(monkeypatch, opens={"count": 1, "hero": 1})

    opener = asyncio.run(scraper._open_photo_grid(object(), place_url=None, place_title=None))

    assert opener == "photo count"
    assert "hero" not in tries


def test_the_owner_photos_come_first_without_duplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    """The business's own uploads lead the gallery; a photo listed in both tabs counts once."""
    scraper = EnrichmentScraper()

    async def open_photo_grid(tab: Any, *, place_url: str | None, place_title: str | None) -> str:
        return "category"

    async def read_open_grid(tab: Any) -> list[str]:
        return ["https://photo/b", "https://photo/c"]

    async def read_photo_category(tab: Any, labels: tuple[str, ...]) -> list[str]:
        return ["https://photo/a", "https://photo/b"]

    monkeypatch.setattr(scraper, "_open_photo_grid", open_photo_grid)
    monkeypatch.setattr(scraper, "_read_open_grid", read_open_grid)
    monkeypatch.setattr(scraper, "_read_photo_category", read_photo_category)

    photos = asyncio.run(scraper._collect_open_grid(object(), seed=["https://photo/known"]))

    assert photos == ["https://photo/known", "https://photo/a", "https://photo/b", "https://photo/c"]
