"""Reading the demo sessions tells "nobody visited" apart from "PostHog could not be read".

A reader that takes an unreadable PostHog for an empty one would see every prospect as silent. Only the demo's
own events make a session: the email events mirrored under the same ``demo_slug`` would date « vu le » at the
last email sent.
"""

import re
from collections.abc import Callable
from datetime import datetime
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from services.posthog_service import DEMO_EVENTS, PostHogService

SINCE = datetime(2026, 10, 1)
EVENT_FILTER_PATTERN = re.compile(r"event IN \(([^)]*)\)")
SESSION_ROW = [
    "garage-nomade",
    "session-1",
    "2026-10-02T08:15:00Z",
    "Mobile",
    "Lausanne",
    6,
    40.0,
    20.0,
    "Europe/Zurich",
    "fr-CH",
    2,
    1,
    3,
    1,
    0,
    "2026-10-02T08:19:30Z",
]


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    def __init__(self, outcome: _FakeResponse | Exception) -> None:
        self._outcome = outcome

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    async def post(self, *args: object, **kwargs: object) -> _FakeResponse:
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


def _configured_service() -> PostHogService:
    service = PostHogService()
    service._project_id = "42"
    service._api_key = "phx_test"
    return service


class _QueryRecordingClient:
    def __init__(self, sent_queries: list[str]) -> None:
        self._sent_queries = sent_queries

    async def __aenter__(self) -> "_QueryRecordingClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    async def post(self, *args: object, json: dict[str, Any], **kwargs: object) -> _FakeResponse:
        self._sent_queries.append(json["query"]["query"])
        return _FakeResponse({"results": [SESSION_ROW]})


def _client_answering(outcome: _FakeResponse | Exception) -> Callable[..., _FakeClient]:
    return lambda **_: _FakeClient(outcome)


@pytest.mark.asyncio
async def test_an_unconfigured_posthog_is_unreadable_not_empty() -> None:
    service = PostHogService()
    service._project_id = ""
    service._api_key = ""

    assert await service.get_demo_sessions(["garage-nomade"], SINCE) is None


@pytest.mark.asyncio
async def test_a_failing_query_is_unreadable_not_empty() -> None:
    with patch.object(httpx, "AsyncClient", _client_answering(httpx.ConnectError("PostHog is down"))):
        assert await _configured_service().get_demo_sessions(["garage-nomade"], SINCE) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{"error": "rate limited"}, {"results": "oops"}, {"results": None}])
async def test_an_answer_without_a_list_of_rows_is_unreadable_not_empty(payload: dict[str, Any]) -> None:
    with patch.object(httpx, "AsyncClient", _client_answering(_FakeResponse(payload))):
        assert await _configured_service().get_demo_sessions(["garage-nomade"], SINCE) is None


@pytest.mark.asyncio
async def test_no_visit_is_an_empty_list() -> None:
    with patch.object(httpx, "AsyncClient", _client_answering(_FakeResponse({"results": []}))):
        assert await _configured_service().get_demo_sessions(["garage-nomade"], SINCE) == []


@pytest.mark.asyncio
async def test_a_session_is_parsed_into_naive_utc() -> None:
    with patch.object(httpx, "AsyncClient", _client_answering(_FakeResponse({"results": [SESSION_ROW]}))):
        sessions = await _configured_service().get_demo_sessions(["garage-nomade"], SINCE)

    assert sessions is not None
    assert [(session.slug, session.started_at, session.city) for session in sessions] == [
        ("garage-nomade", datetime(2026, 10, 2, 8, 15), "Lausanne")
    ]
    assert [
        (session.timezone_name, session.language, session.pageview_count, session.engaged_count) for session in sessions
    ] == [("Europe/Zurich", "fr-CH", 2, 1)]
    assert [
        (session.cta_click_count, session.phone_click_count, session.contact_click_count, session.last_event_at)
        for session in sessions
    ] == [(3, 1, 0, datetime(2026, 10, 2, 8, 19, 30))]


@pytest.mark.asyncio
async def test_the_whole_history_reads_only_the_demo_events_from_their_first_day() -> None:
    """The hot leads read every session ever made on the demos, and only from the demo's own events."""
    sent_queries: list[str] = []
    with patch.object(httpx, "AsyncClient", lambda **_: _QueryRecordingClient(sent_queries)):
        sessions = await _configured_service().get_demo_sessions(["garage-nomade"])

    assert sessions is not None and len(sessions) == 1
    assert len(sent_queries) == 1
    assert "timestamp >=" not in sent_queries[0]
    event_filter = EVENT_FILTER_PATTERN.search(sent_queries[0])
    assert event_filter is not None
    filtered_events = {event_name.strip(" '") for event_name in event_filter.group(1).split(",")}
    assert filtered_events == set(DEMO_EVENTS)


@pytest.mark.asyncio
async def test_no_slug_to_read_is_an_empty_list_without_asking_posthog() -> None:
    service = PostHogService()
    service._project_id = ""
    service._api_key = ""

    assert await service.get_demo_sessions([], SINCE) == []
