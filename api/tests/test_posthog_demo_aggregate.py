"""The demo aggregate behind the hot leads counts only the demo's own events.

The email events mirrored under the same ``demo_slug`` would date « vu le » at the last email sent,
and a session holding only a page leave would add a visit to the lead score.
"""

import re
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from services.posthog_service import DEMO_EVENTS, PostHogService

EVENT_FILTER_PATTERN = re.compile(r"event IN \(([^)]*)\)")
AGGREGATE_ROW = ["garage-nomade", 3, 2, 0, 0, 1, 4, 0, "2026-10-26T15:26:26Z"]


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _QueryRecordingClient:
    def __init__(self, sent_queries: list[str]) -> None:
        self._sent_queries = sent_queries

    async def __aenter__(self) -> "_QueryRecordingClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    async def post(self, *args: object, json: dict[str, Any], **kwargs: object) -> _FakeResponse:
        self._sent_queries.append(json["query"]["query"])
        return _FakeResponse({"results": [AGGREGATE_ROW]})


def _configured_service() -> PostHogService:
    service = PostHogService()
    service._project_id = "42"
    service._api_key = "phx_test"
    return service


@pytest.mark.asyncio
async def test_the_aggregate_reads_only_the_demo_events() -> None:
    sent_queries: list[str] = []
    with patch.object(httpx, "AsyncClient", lambda **_: _QueryRecordingClient(sent_queries)):
        aggregate = await _configured_service().get_aggregate_by_slugs(["garage-nomade"])

    assert len(sent_queries) == 1
    event_filter = EVENT_FILTER_PATTERN.search(sent_queries[0])
    assert event_filter is not None
    filtered_events = {event_name.strip(" '") for event_name in event_filter.group(1).split(",")}
    assert filtered_events == set(DEMO_EVENTS)
    assert aggregate["garage-nomade"]["visits"] == 2
    assert aggregate["garage-nomade"]["last_seen"] == "2026-10-26T15:26:26Z"
