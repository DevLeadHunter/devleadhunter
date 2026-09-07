"""Reordering a launched campaign re-dates its pending J1 sends to the new prospect order.

The queue is materialised at launch (a fixed ``scheduled_at`` per J1), so ``reschedule_pending_initial``
re-pairs the ascending send slots to the campaign's prospects in ``position`` order — the prospect
placed 2nd gets the 2nd slot, so it goes out on the 2nd day. Prospects already sent (no pending row)
are excluded, and the slot computation excludes the campaign's own pending rows from the caps while
reserving the days its sent J1s already used.
"""

from datetime import date, datetime
from types import SimpleNamespace

from services.campaign_queue_service import CampaignQueueService


class _Result:
    """Stand-in for a SQLAlchemy Result, answering ``scalars()`` with a fixed list."""

    def __init__(self, scalars: list[object]) -> None:
        self._scalars = scalars

    def scalars(self) -> list[object]:
        return list(self._scalars)


class _FakeDB:
    """Session stand-in returning pre-programmed results in call order and counting commits."""

    def __init__(self, results: list[_Result]) -> None:
        self._results = list(results)
        self.commits = 0

    def execute(self, *args: object, **kwargs: object) -> _Result:
        return self._results.pop(0)

    def commit(self) -> None:
        self.commits += 1


def _pending_item(prospect_id: int, scheduled_at: datetime | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        prospect_id=prospect_id,
        queue_type="initial",
        status="pending",
        scheduled_at=scheduled_at or datetime(2026, 9, 7, 8, 0, 0),
    )


def test_reschedule_pairs_slots_to_prospects_in_position_order() -> None:
    # campaign.prospects is ordered by position; the queue holds one pending J1 per prospect.
    item_first = _pending_item(30)
    item_second = _pending_item(10)
    item_third = _pending_item(20)
    campaign = SimpleNamespace(
        id=6,
        prospects=[SimpleNamespace(id=30), SimpleNamespace(id=10), SimpleNamespace(id=20)],
    )
    db = _FakeDB([_Result(scalars=[item_second, item_third, item_first])])  # query order is irrelevant
    service = CampaignQueueService(db)
    slots = [datetime(2026, 9, 8, 8, 0), datetime(2026, 9, 9, 8, 0), datetime(2026, 9, 10, 8, 0)]
    service._reschedule_slots = lambda campaign_arg, ordered: slots  # type: ignore[method-assign]

    moved = service.reschedule_pending_initial(campaign)

    assert moved == 3
    # First prospect by position (id 30) gets the earliest slot, then id 10, then id 20.
    assert item_first.scheduled_at == slots[0]
    assert item_second.scheduled_at == slots[1]
    assert item_third.scheduled_at == slots[2]
    assert db.commits == 1


def test_reschedule_skips_prospects_without_a_pending_send() -> None:
    # id 30 is already sent (no pending row) → only the two pending prospects move, in position order.
    item_second = _pending_item(10)
    item_third = _pending_item(20)
    campaign = SimpleNamespace(
        id=6,
        prospects=[SimpleNamespace(id=30), SimpleNamespace(id=10), SimpleNamespace(id=20)],
    )
    db = _FakeDB([_Result(scalars=[item_second, item_third])])
    service = CampaignQueueService(db)
    captured: dict[str, list[object]] = {}
    slots = [datetime(2026, 9, 8, 8, 0), datetime(2026, 9, 9, 8, 0)]

    def _fake_slots(campaign_arg: object, ordered: list[object]) -> list[datetime]:
        captured["ordered"] = ordered
        return slots

    service._reschedule_slots = _fake_slots  # type: ignore[method-assign]

    moved = service.reschedule_pending_initial(campaign)

    assert moved == 2
    assert captured["ordered"] == [item_second, item_third]  # id 10 before id 20 (position order)
    assert item_second.scheduled_at == slots[0]
    assert item_third.scheduled_at == slots[1]


def test_reschedule_is_a_noop_without_pending_sends() -> None:
    campaign = SimpleNamespace(id=6, prospects=[SimpleNamespace(id=10)])
    db = _FakeDB([_Result(scalars=[])])
    service = CampaignQueueService(db)

    moved = service.reschedule_pending_initial(campaign)

    assert moved == 0
    assert db.commits == 0


def test_reschedule_slots_drops_own_pending_and_seeds_sent_days(monkeypatch) -> None:
    # The campaign's own pending J1 must not block itself, while a day its sent J1 used stays full.
    from services.send_policy_service import send_policy_service

    own_slot = datetime(2026, 9, 8, 8, 0)
    campaign = SimpleNamespace(id=6, user_id=1, max_emails_per_day=1, send_delay_minutes=20)
    pending_items = [_pending_item(10, own_slot)]

    monkeypatch.setattr(send_policy_service, "get_policy", lambda db, user_id: object())
    monkeypatch.setattr(send_policy_service, "resolve", lambda db, user_id: "resolved-policy")
    monkeypatch.setattr(
        send_policy_service, "pending_schedule", lambda db, user_id: ({date(2026, 9, 8): 1}, {own_slot})
    )
    monkeypatch.setattr(
        send_policy_service, "pending_campaign_counts_by_day", lambda db, campaign_id: {date(2026, 9, 8): 1}
    )
    monkeypatch.setattr(
        send_policy_service, "sent_campaign_counts_by_day", lambda db, campaign_id: {date(2026, 9, 7): 1}
    )

    captured: dict[str, object] = {}

    def _fake_next_send_slots(policy: object, count: int, **kwargs: object) -> list[datetime]:
        captured["seed_counts"] = dict(kwargs["seed_counts"])
        captured["occupied"] = set(kwargs["occupied"])
        captured["campaign_seed_counts"] = dict(kwargs["campaign_seed_counts"])
        captured["per_campaign_cap"] = kwargs["per_campaign_cap"]
        return [datetime(2026, 9, 9, 8, 0) for _ in range(count)]

    monkeypatch.setattr(send_policy_service, "next_send_slots", _fake_next_send_slots)

    slots = CampaignQueueService(_FakeDB([]))._reschedule_slots(campaign, pending_items)

    assert len(slots) == 1
    # The one pending row on the 8th was this campaign's own → removed from the global day count…
    assert captured["seed_counts"] == {}
    # …and from the occupied instants, so it does not collide with itself.
    assert captured["occupied"] == set()
    # The day the sent J1 used stays reserved against the per-campaign cap.
    assert captured["campaign_seed_counts"] == {date(2026, 9, 7): 1}
    assert captured["per_campaign_cap"] == 1
