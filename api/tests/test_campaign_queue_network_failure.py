"""
When an email does not leave because Resend is unreachable, the queue re-plans it by itself inside the
prospect's sending window, a bounded number of times, then fails it and warns the admins.
"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from services import campaign_queue_service as queue_module
from services.campaign_queue_service import CampaignQueueService
from services.notification_service import notification_service
from services.send_policy_service import ResolvedPolicy, send_policy_service

_NOON_UTC = datetime(2026, 10, 21, 10, 0)
_AT_NIGHT_UTC = datetime(2026, 10, 20, 20, 0)
_NEXT_WINDOW_START_UTC = datetime(2026, 10, 21, 6, 0)
_NETWORK_FAILURE = {"success": False, "error": "Resend injoignable après 4 essais", "error_kind": "network"}
_PROVIDER_REFUSAL = {"success": False, "error": "Resend API error 422", "error_kind": "provider"}


class _FakeDB:
    """Session stand-in — these transitions only ever ``commit``."""

    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


def _item(send_attempts: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        id=7, user_id=1, status="sending", scheduled_at=_NOON_UTC, skip_reason=None, send_attempts=send_attempts
    )


def _swiss_prospect() -> SimpleNamespace:
    return SimpleNamespace(id=263, name="Jantes Alu", country="CH")


def _default_policy(_db: object, _user_id: int) -> ResolvedPolicy:
    return ResolvedPolicy(
        daily_cap=22,
        days_of_week=[0, 1, 2, 3, 4],
        window_start_hour=8,
        window_end_hour=18,
        spacing_minutes=30,
        follow_up_delay_days=3,
    )


def _freeze(monkeypatch: pytest.MonkeyPatch, now_utc: datetime) -> list[dict[str, object]]:
    """Fix the clock and the policy, and record the admin notifications instead of sending them."""
    notifications: list[dict[str, object]] = []

    async def record(**kwargs: object) -> None:
        notifications.append(kwargs)

    monkeypatch.setattr(queue_module, "_utcnow", lambda: now_utc)
    monkeypatch.setattr(send_policy_service, "resolve", _default_policy)
    monkeypatch.setattr(notification_service, "notify_error", record)
    return notifications


@pytest.mark.asyncio
async def test_a_provider_refusal_fails_the_item_at_once(monkeypatch: pytest.MonkeyPatch) -> None:
    notifications = _freeze(monkeypatch, _NOON_UTC)
    db = _FakeDB()
    item = _item()

    await CampaignQueueService(db)._settle_failed_send(item, _swiss_prospect(), _PROVIDER_REFUSAL)

    assert item.status == "failed"
    assert item.send_attempts == 0
    assert notifications == []


@pytest.mark.asyncio
async def test_a_network_cut_re_plans_the_item_ten_minutes_later(monkeypatch: pytest.MonkeyPatch) -> None:
    notifications = _freeze(monkeypatch, _NOON_UTC)
    db = _FakeDB()
    item = _item()

    await CampaignQueueService(db)._settle_failed_send(item, _swiss_prospect(), _NETWORK_FAILURE)

    assert item.status == "pending"
    assert item.send_attempts == 1
    assert item.scheduled_at == datetime(2026, 10, 21, 10, 10)
    assert notifications == []
    assert db.commits == 1


@pytest.mark.asyncio
async def test_a_network_cut_at_night_re_plans_for_the_next_window_start(monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze(monkeypatch, _AT_NIGHT_UTC)
    db = _FakeDB()
    item = _item(send_attempts=1)

    await CampaignQueueService(db)._settle_failed_send(item, _swiss_prospect(), _NETWORK_FAILURE)

    assert item.status == "pending"
    assert item.send_attempts == 2
    assert item.scheduled_at == _NEXT_WINDOW_START_UTC


@pytest.mark.asyncio
async def test_the_fourth_network_cut_fails_the_item_and_warns_the_admins(monkeypatch: pytest.MonkeyPatch) -> None:
    notifications = _freeze(monkeypatch, _NOON_UTC)
    db = _FakeDB()
    item = _item(send_attempts=3)

    await CampaignQueueService(db)._settle_failed_send(item, _swiss_prospect(), _NETWORK_FAILURE)

    assert item.status == "failed"
    assert item.send_attempts == 4
    assert len(notifications) == 1
    assert notifications[0]["tag"] == "send-network-failure"
    assert "Jantes Alu" in str(notifications[0]["message"])
