"""Manual queue controls replace the old auto-skip-on-open rule.

A relance no longer stops itself when the prospect opens the J1 (opens are noisy — bot/proxy
prefetch inflates them). Instead the operator drives sends by hand from the campaign queue:
cancel a pending item so it never goes out, or re-queue a skipped one so the worker sends it on
its next tick. Both are guarded status transitions — only a ``pending`` item cancels, only a
``skipped`` item re-sends.
"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from services import campaign_queue_service as queue_module
from services.campaign_queue_service import CampaignQueueService
from services.send_policy_service import ResolvedPolicy, send_policy_service


class _FakeDB:
    """Session stand-in — these transitions only ever ``commit``."""

    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


def _item(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 7,
        "user_id": 1,
        "prospect": None,
        "status": "pending",
        "skip_reason": None,
        "scheduled_at": "2026-08-28T09:47:00",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_cancel_marks_a_pending_item_skipped_with_a_manual_reason() -> None:
    db = _FakeDB()
    item = _item(status="pending")

    CampaignQueueService(db).cancel_queue_item(item)

    assert item.status == "skipped"
    assert item.skip_reason == "Annulé manuellement"
    assert db.commits == 1


def test_cancel_rejects_an_item_that_is_not_pending() -> None:
    db = _FakeDB()
    item = _item(status="sent")

    with pytest.raises(ValueError):
        CampaignQueueService(db).cancel_queue_item(item)

    assert item.status == "sent"
    assert db.commits == 0


_INSIDE_THE_WINDOW_UTC = datetime(2026, 10, 21, 9, 0)
_AT_NIGHT_UTC = datetime(2026, 10, 20, 20, 0)
_NEXT_WINDOW_START_UTC = datetime(2026, 10, 21, 6, 0)


def _default_policy(_db: object, _user_id: int) -> ResolvedPolicy:
    """Léo's policy: weekdays, 8 a.m. to 6 p.m. Paris."""
    return ResolvedPolicy(
        daily_cap=22,
        days_of_week=[0, 1, 2, 3, 4],
        window_start_hour=8,
        window_end_hour=18,
        spacing_minutes=30,
        follow_up_delay_days=3,
    )


def _freeze_requeue_clock(monkeypatch: pytest.MonkeyPatch, now_utc: datetime) -> None:
    monkeypatch.setattr(queue_module, "_utcnow", lambda: now_utc)
    monkeypatch.setattr(send_policy_service, "resolve", _default_policy)


def test_requeue_inside_the_window_puts_a_skipped_item_back_to_pending_now(monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze_requeue_clock(monkeypatch, _INSIDE_THE_WINDOW_UTC)
    db = _FakeDB()
    item = _item(status="skipped", skip_reason="Annulé manuellement")

    CampaignQueueService(db).requeue_item(item)

    assert item.status == "pending"
    assert item.skip_reason is None
    assert item.scheduled_at == _INSIDE_THE_WINDOW_UTC
    assert db.commits == 1


def test_requeue_at_night_waits_for_the_next_window_start(monkeypatch: pytest.MonkeyPatch) -> None:
    """A send that failed at noon and is re-queued at 10 p.m. leaves at 8 a.m. the next day."""
    _freeze_requeue_clock(monkeypatch, _AT_NIGHT_UTC)
    db = _FakeDB()
    item = _item(status="failed")

    CampaignQueueService(db).requeue_item(item)

    assert item.status == "pending"
    assert item.scheduled_at == _NEXT_WINDOW_START_UTC
    assert db.commits == 1


def test_requeue_rejects_an_item_that_is_neither_skipped_nor_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze_requeue_clock(monkeypatch, _INSIDE_THE_WINDOW_UTC)
    db = _FakeDB()
    item = _item(status="pending")

    with pytest.raises(ValueError):
        CampaignQueueService(db).requeue_item(item)

    assert item.status == "pending"
    assert db.commits == 0
