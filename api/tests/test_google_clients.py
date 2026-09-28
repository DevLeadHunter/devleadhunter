"""The Google clients over HTTP: Google is never called, its answers come from an httpx MockTransport."""

import asyncio
from datetime import datetime
from typing import Any

import httpx
import pytest

import services.ai_assistant.google_calendar_client as google_module
from services.ai_assistant.google_calendar_client import CalendarEventState, GoogleCalendarClient


def _calendar_client_with(handler: Any, monkeypatch: pytest.MonkeyPatch) -> GoogleCalendarClient:
    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def patched_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(google_module.httpx, "AsyncClient", patched_client)
    monkeypatch.setattr(google_module.settings, "google_client_id", "client-id")
    monkeypatch.setattr(google_module.settings, "google_client_secret", "client-secret")
    return GoogleCalendarClient()


def test_the_calendar_client_reads_back_an_event_it_created(monkeypatch: pytest.MonkeyPatch) -> None:
    """The reminder and the booking recovery read our event: still there, moved, cancelled or gone."""
    requested: list[str] = []
    answers = iter(
        [
            httpx.Response(200, json={"status": "confirmed", "start": {"dateTime": "2026-09-24T14:00:00+02:00"}}),
            httpx.Response(200, json={"status": "cancelled"}),
            httpx.Response(410, json={"error": {"message": "Resource has been deleted"}}),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.raw_path.decode())
        return next(answers)

    client = _calendar_client_with(handler, monkeypatch)
    standing = asyncio.run(client.get_event("a", "agenda du garage@group.calendar.google.com", "dlh1abc"))
    cancelled = asyncio.run(client.get_event("a", "primary", "dlh1abc"))
    deleted = asyncio.run(client.get_event("a", "primary", "dlh1abc"))

    assert standing == CalendarEventState(cancelled=False, start=datetime(2026, 9, 24, 12, 0))
    assert cancelled == CalendarEventState(cancelled=True, start=None)
    assert deleted is None
    assert requested[0] == "/calendar/v3/calendars/agenda%20du%20garage%40group.calendar.google.com/events/dlh1abc"
