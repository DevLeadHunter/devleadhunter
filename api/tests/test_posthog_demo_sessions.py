"""Reading the demo sessions tells "nobody visited" apart from "PostHog could not be read".

A reader that takes an unreadable PostHog for an empty one would see every prospect as silent.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from services.posthog_service import PostHogService

SINCE = datetime(2026, 10, 1)
SESSION_ROW = ["garage-nomade", "session-1", "2026-10-02T08:15:00Z", "Mobile", "Lausanne", 6, 40.0, 20.0]


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


@pytest.mark.asyncio
async def test_no_slug_to_read_is_an_empty_list_without_asking_posthog() -> None:
    service = PostHogService()
    service._project_id = ""
    service._api_key = ""

    assert await service.get_demo_sessions([], SINCE) == []
