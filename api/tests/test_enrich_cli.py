"""The enrichment tool keeps a scrape through an API restart: a passing error is tried again, a refusal is not."""

import asyncio
from typing import Any

import httpx
import pytest

import enrich_cli
from scrappers.enrichment_scraper import EnrichmentData


class _RestartingApi:
    """An API answering 502 while a deployment restarts it, then the enrichment record."""

    def __init__(self, statuses: list[int]) -> None:
        self._statuses = statuses
        self.post_count = 0

    async def post(self, path: str, *, json: Any = None) -> httpx.Response:
        status = self._statuses[min(self.post_count, len(self._statuses) - 1)]
        self.post_count += 1
        request = httpx.Request("POST", f"https://api.example{path}")
        return httpx.Response(status, json={"status": "completed"} if status == 200 else {}, request=request)


@pytest.fixture(autouse=True)
def no_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    async def instantly(seconds: float) -> None:
        return None

    monkeypatch.setattr(enrich_cli.asyncio, "sleep", instantly)


def test_a_save_answered_502_during_a_deployment_is_tried_again() -> None:
    """Alex'Élec's scrape was lost on a 502 while the API restarted."""
    api = _RestartingApi([502, 502, 200])

    record = asyncio.run(enrich_cli._persist(api, 403, EnrichmentData(rating=4.9)))  # type: ignore[arg-type]

    assert (record, api.post_count) == ({"status": "completed"}, 3)


def test_a_refused_save_is_not_tried_again() -> None:
    api = _RestartingApi([422])

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(enrich_cli._persist(api, 403, EnrichmentData(rating=4.9)))  # type: ignore[arg-type]

    assert api.post_count == 1
