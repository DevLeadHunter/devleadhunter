"""The campaign queue hands the scheduler each prospect's timezone, read from its country.

``_schedule_slots`` passes one zone per prospect (in send order) and ``_schedule_follow_ups`` counts
the follow-up on the J1 prospect's clock. The legacy spacing path (no SendPolicy, no campaign cap)
has no window, so it has no zone to honour and stays as it was.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

from services.campaign_queue_service import CampaignQueueService
from services.send_policy_service import send_policy_service


class _Result:
    """Stand-in for a SQLAlchemy Result answering ``scalars().all()`` with a fixed list."""

    def __init__(self, scalars: list[object]) -> None:
        self._scalars = scalars

    def scalars(self) -> SimpleNamespace:
        return SimpleNamespace(all=lambda: list(self._scalars))


class _FakeDB:
    """Session stand-in: pre-programmed results, recorded rows."""

    def __init__(self, results: list[_Result] | None = None) -> None:
        self._results = list(results or [])
        self.added: list[object] = []
        self.commits = 0

    def execute(self, *args: object, **kwargs: object) -> _Result:
        return self._results.pop(0)

    def add(self, row: object) -> None:
        self.added.append(row)

    def commit(self) -> None:
        self.commits += 1


def _prospect(prospect_id: int, country: str) -> SimpleNamespace:
    return SimpleNamespace(id=prospect_id, country=country)


def test_prospect_timezone_reads_the_country_profile() -> None:
    assert CampaignQueueService.prospect_timezone(_prospect(1, "FR")) == "Europe/Paris"
    assert CampaignQueueService.prospect_timezone(_prospect(2, "ch")) == "Europe/Zurich"
    assert CampaignQueueService.prospect_timezone(_prospect(3, "BE")) == "Europe/Brussels"
    # A missing prospect or an unknown country reads as France, like everywhere in the product.
    assert CampaignQueueService.prospect_timezone(None) == "Europe/Paris"
    assert CampaignQueueService.prospect_timezone(_prospect(4, "ZZ")) == "Europe/Paris"


def test_schedule_slots_passes_one_zone_per_prospect_in_send_order(monkeypatch) -> None:
    campaign = SimpleNamespace(id=6, user_id=1, max_emails_per_day=1, send_delay_minutes=20)
    monkeypatch.setattr(send_policy_service, "get_policy", lambda db, user_id: object())
    monkeypatch.setattr(send_policy_service, "resolve", lambda db, user_id: SimpleNamespace(spacing_minutes=20))
    monkeypatch.setattr(send_policy_service, "pending_schedule", lambda db, user_id: ({}, set()))
    monkeypatch.setattr(send_policy_service, "pending_campaign_counts_by_day", lambda db, campaign_id: {})
    captured: dict[str, object] = {}

    def _fake_next_send_slots(policy: object, count: int, **kwargs: object) -> list[datetime]:
        captured["count"] = count
        captured["slot_timezones"] = list(kwargs["slot_timezones"])
        return [datetime(2026, 10, 5, 12, 0) + timedelta(days=index) for index in range(count)]

    monkeypatch.setattr(send_policy_service, "next_send_slots", _fake_next_send_slots)

    prospects = [_prospect(10, "FR"), _prospect(20, "CH"), _prospect(30, "BE")]
    slots = CampaignQueueService(_FakeDB())._schedule_slots(campaign, prospects, datetime(2026, 10, 5, 5, 0), None)

    assert len(slots) == 3
    assert captured["count"] == 3
    assert captured["slot_timezones"] == ["Europe/Paris", "Europe/Zurich", "Europe/Brussels"]


def test_legacy_spacing_ignores_the_window_and_the_zones(monkeypatch) -> None:
    campaign = SimpleNamespace(id=6, user_id=1, max_emails_per_day=None, send_delay_minutes=30)
    monkeypatch.setattr(send_policy_service, "get_policy", lambda db, user_id: None)
    monkeypatch.setattr(
        send_policy_service,
        "next_send_slots",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("the legacy path must not use the policy")),
    )
    now = datetime(2026, 10, 10, 2, 0)  # a Saturday night: no window applies on this path

    slots = CampaignQueueService(_FakeDB())._schedule_slots(
        campaign, [_prospect(1, "CH"), _prospect(2, "FR")], now, None
    )

    assert slots == [now, now + timedelta(minutes=30)]


def test_follow_ups_are_counted_on_the_j1_prospect_clock(monkeypatch) -> None:
    campaign = SimpleNamespace(id=6, user_id=1, follow_up_template_id=None)
    steps = [
        SimpleNamespace(template_id=42, sms_template_key=None, delay_days=3, position=1),
        SimpleNamespace(template_id=43, sms_template_key=None, delay_days=2, position=2),
    ]
    j1_item = SimpleNamespace(
        id=1,
        user_id=1,
        campaign_id=6,
        prospect_id=20,
        ab_variant=None,
        campaign=campaign,
        prospect=_prospect(20, "CH"),
    )
    db = _FakeDB([_Result(scalars=steps)])
    service = CampaignQueueService(db)
    service._offer_link_outlives = lambda item, scheduled_at, **template: True  # type: ignore[method-assign]
    monkeypatch.setattr(send_policy_service, "resolve", lambda db, user_id: "resolved-policy")
    captured: list[tuple[int, str]] = []

    def _fake_follow_up_slot(policy: object, sent_at: datetime, delay_days: int, *, timezone_name: str) -> datetime:
        captured.append((delay_days, timezone_name))
        return sent_at + timedelta(days=delay_days)

    monkeypatch.setattr(send_policy_service, "follow_up_slot", _fake_follow_up_slot)

    service._schedule_follow_ups(j1_item)

    assert captured == [(3, "Europe/Zurich"), (5, "Europe/Zurich")]
    assert [row.template_id for row in db.added] == [42, 43]
    assert db.commits == 1
