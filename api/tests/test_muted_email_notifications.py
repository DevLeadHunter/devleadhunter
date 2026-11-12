"""The « mail envoyé » and « mail livré » notifications are switched off: logged in the activity feed, never notified."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

import services.notification_service as notification_module
from services.notification_service import NotificationService


@pytest.fixture
def logged_actions(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The actions written to the activity feed, none of them really stored."""
    actions: list[str] = []

    def record(**entry: object) -> None:
        actions.append(str(entry["action"]))

    monkeypatch.setattr(notification_module.activity_log_service, "record", record)
    return actions


@pytest.fixture
def dispatched(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """The notifications the service raised, none of them stored or pushed."""
    dispatch = AsyncMock()
    monkeypatch.setattr(NotificationService, "_dispatch", dispatch)
    monkeypatch.setattr(
        NotificationService, "_resolve_prospect_name", staticmethod(lambda _db, _id, fallback: fallback)
    )
    return dispatch


def _raise_email_event(event_name: str) -> None:
    asyncio.run(
        NotificationService().notify_email_event(
            None,
            user_id=1,
            event_name=event_name,
            recipient_email="garage@example.fr",
            prospect_id=12,
            subject="le site de Garage Test",
            email_log_id=34,
        )
    )


@pytest.mark.parametrize("event_name", ["email_sent", "email_delivered"])
def test_a_muted_email_event_is_logged_without_notifying(
    event_name: str, logged_actions: list[str], dispatched: AsyncMock
) -> None:
    """A sent or delivered email keeps its line in the activity feed and raises no notification."""
    _raise_email_event(event_name)

    assert logged_actions == [event_name]
    dispatched.assert_not_awaited()


@pytest.mark.parametrize("event_name", ["email_clicked", "email_bounced", "email_replied", "email_failed"])
def test_the_other_email_events_still_notify(event_name: str, logged_actions: list[str], dispatched: AsyncMock) -> None:
    """Every email event that was not switched off is logged and notified as before."""
    _raise_email_event(event_name)

    assert logged_actions == [event_name]
    dispatched.assert_awaited_once()
    assert dispatched.await_args.kwargs["category"] == "email"


def test_emptying_the_muted_set_notifies_a_sent_email_again(
    monkeypatch: pytest.MonkeyPatch, logged_actions: list[str], dispatched: AsyncMock
) -> None:
    """The switch is the set alone: emptied, a sent email is notified again with its usual wording."""
    monkeypatch.setattr(notification_module, "_MUTED_EMAIL_EVENTS", frozenset())

    _raise_email_event("email_sent")

    dispatched.assert_awaited_once()
    assert dispatched.await_args.kwargs["body"] == "Mail envoyé"
