"""
Unit tests for the send-policy slot scheduler.

The structural invariants (window, weekdays, spacing, daily cap) are asserted on the
sender's clock, as before. The prospect-timezone cases pin exact instants: Montréal
(``America/Toronto``) is UTC−4 until the 1st of November 2026 and UTC−5 afterwards,
while Paris goes from UTC+2 to UTC+1 on the 25th of October 2026, so a week sits
between the two changes.
"""

import itertools
from datetime import date, datetime

import pytest

from services.send_policy_service import SENDER_TIMEZONE, ResolvedPolicy, _to_local, send_policy_service

MONTREAL: str = "America/Toronto"


def _local(moment: datetime) -> datetime:
    """Convert a returned naive-UTC slot to the sender's clock for assertions."""
    return _to_local(moment, SENDER_TIMEZONE)


def _policy(window_start_hour: int = 7, daily_cap: int = 20) -> ResolvedPolicy:
    """A Mon–Fri, 07:00–18:00 (or later start), 1/20min, 20/day policy."""
    return ResolvedPolicy(
        daily_cap=daily_cap,
        days_of_week=[0, 1, 2, 3, 4],
        window_start_hour=window_start_hour,
        window_end_hour=18,
        spacing_minutes=20,
        follow_up_delay_days=5,
    )


def _sender_days(slots: list[datetime]) -> dict[date, int]:
    """Count slots per sender day, the day the cap is counted on."""
    per_day: dict[date, int] = {}
    for slot in slots:
        day = _local(slot).date()
        per_day[day] = per_day.get(day, 0) + 1
    return per_day


def test_count_and_order() -> None:
    """It returns exactly ``count`` ascending slots."""
    slots = send_policy_service.next_send_slots(_policy(), 50)
    assert len(slots) == 50
    assert slots == sorted(slots)


def test_slots_stay_in_window_and_weekdays() -> None:
    """Every slot falls on an allowed weekday inside the hour window."""
    policy = _policy()
    slots = send_policy_service.next_send_slots(policy, 60)
    for slot in slots:
        local = _local(slot)
        assert local.weekday() in policy.days_of_week
        assert policy.window_start_hour <= local.hour < policy.window_end_hour


def test_daily_cap_respected() -> None:
    """No sender calendar day exceeds the daily cap."""
    policy = ResolvedPolicy(5, [0, 1, 2, 3, 4], 7, 18, 20, 5)
    slots = send_policy_service.next_send_slots(policy, 23)
    per_day = _sender_days(slots)
    assert max(per_day.values()) <= 5
    # 23 items at 5/day → spread over at least 5 days.
    assert len(per_day) >= 5


def test_spacing_within_day() -> None:
    """Two slots on the same local day are at least ``spacing_minutes`` apart."""
    policy = _policy()
    slots = send_policy_service.next_send_slots(policy, 10)
    for earlier, later in itertools.pairwise(slots):
        le, ll = _local(earlier), _local(later)
        if le.date() == ll.date():
            assert (ll - le).total_seconds() >= policy.spacing_minutes * 60 - 1


def test_seed_counts_pushes_to_next_day() -> None:
    """A day already at the cap gets no new slots."""
    policy = ResolvedPolicy(3, [0, 1, 2, 3, 4], 7, 18, 20, 5)
    start = datetime(2026, 7, 13, 6, 0, 0)  # Monday, before the window (UTC)
    first_local_day = _local(start).date()
    slots = send_policy_service.next_send_slots(policy, 3, start_utc=start, seed_counts={first_local_day: 3})
    assert all(_local(s).date() != first_local_day for s in slots)


def test_per_campaign_cap_limits_slots_per_day() -> None:
    """A per-campaign cap of 1 spreads the campaign at one send per day, below the global cap."""
    slots = send_policy_service.next_send_slots(_policy(), 5, per_campaign_cap=1)
    per_day = _sender_days(slots)
    assert len(slots) == 5
    assert max(per_day.values()) == 1
    assert len(per_day) == 5


def test_campaign_seed_counts_pushes_to_next_day() -> None:
    """A day where this campaign already used its cap gets no new slot."""
    start = datetime(2026, 8, 24, 5, 0, 0)  # Monday
    first_local_day = _local(start).date()
    slots = send_policy_service.next_send_slots(
        _policy(), 2, start_utc=start, per_campaign_cap=1, campaign_seed_counts={first_local_day: 1}
    )
    assert all(_local(s).date() != first_local_day for s in slots)


def test_occupied_slots_are_skipped() -> None:
    """Instants already taken by other pending emails are never reused."""
    policy = _policy()
    start = datetime(2026, 8, 24, 5, 0, 0)  # Monday
    first = send_policy_service.next_send_slots(policy, 3, start_utc=start)
    second = send_policy_service.next_send_slots(policy, 3, start_utc=start, occupied=set(first))
    assert set(first).isdisjoint(second)


class _FakeResult:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[object, ...]]:
        return self._rows


class _FakeDB:
    """Session stand-in whose ``execute(...).all()`` returns fixed ``(scheduled_at, queue_type)`` rows."""

    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows

    def execute(self, *args: object, **kwargs: object) -> _FakeResult:
        return _FakeResult(self._rows)


def test_follow_ups_do_not_consume_the_daily_cap() -> None:
    """A follow-up reserves its exact instant but never counts toward a day's cap — only J1s do."""
    rows: list[tuple[object, ...]] = [
        (datetime(2026, 8, 28, 6, 0, 0), "initial"),
        (datetime(2026, 8, 28, 7, 0, 0), "followup"),
        (datetime(2026, 8, 28, 8, 0, 0), "followup"),
    ]
    counts, occupied = send_policy_service.pending_schedule(_FakeDB(rows), user_id=1)

    day = _local(datetime(2026, 8, 28, 6, 0, 0)).date()
    assert counts.get(day) == 1
    assert len(occupied) == 3


def test_two_campaigns_interleave_one_per_day() -> None:
    """Two 1/day campaigns launched together land one of each on the same days, at distinct instants."""
    policy = _policy()  # global cap 20
    start = datetime(2026, 8, 24, 5, 0, 0)  # Monday

    campaign_a = send_policy_service.next_send_slots(policy, 3, start_utc=start, per_campaign_cap=1)

    campaign_b = send_policy_service.next_send_slots(
        policy, 3, start_utc=start, seed_counts=_sender_days(campaign_a), occupied=set(campaign_a), per_campaign_cap=1
    )

    days_a = [_local(s).date() for s in campaign_a]
    days_b = [_local(s).date() for s in campaign_b]
    assert days_a == days_b  # both campaigns cover the same three days
    assert set(campaign_a).isdisjoint(campaign_b)  # spaced, never the same instant


def test_canadian_prospect_slot_is_eight_in_montreal_fourteen_in_paris() -> None:
    """A Monday 8 a.m. in Montréal is 12:00 UTC in October — 2 p.m. in Paris, not 2 a.m. in Montréal."""
    start = datetime(2026, 10, 5, 0, 0, 0)  # Monday 00:00 UTC = Sunday 20:00 in Montréal
    slots = send_policy_service.next_send_slots(
        _policy(window_start_hour=8), 1, start_utc=start, slot_timezones=[MONTREAL]
    )
    assert slots == [datetime(2026, 10, 5, 12, 0, 0)]
    assert _to_local(slots[0], MONTREAL) == datetime(2026, 10, 5, 8, 0, 0)
    assert _local(slots[0]) == datetime(2026, 10, 5, 14, 0, 0)


def test_slot_keeps_eight_in_montreal_across_both_winter_time_changes() -> None:
    """Paris changes on the 25th of October, Montréal on the 1st of November: the local hour never moves."""
    start = datetime(2026, 10, 19, 0, 0, 0)  # Monday
    slots = send_policy_service.next_send_slots(
        _policy(window_start_hour=8), 15, start_utc=start, per_campaign_cap=1, slot_timezones=[MONTREAL] * 15
    )
    montreal = [_to_local(slot, MONTREAL) for slot in slots]
    assert all(moment.hour == 8 and moment.minute == 0 for moment in montreal)
    assert all(moment.weekday() < 5 for moment in montreal)
    # Same wall clock in Montréal, three different UTC/Paris readings over the three weeks.
    assert [slot.hour for slot in slots] == [12] * 10 + [13] * 5
    assert [_local(slot).hour for slot in slots] == [14] * 5 + [13] * 5 + [14] * 5


def test_no_slot_on_the_prospect_local_weekend() -> None:
    """Saturday 02:00 UTC is still Friday evening in Montréal: the next slot is Monday 7 a.m. there."""
    start = datetime(2026, 10, 10, 2, 0, 0)
    slots = send_policy_service.next_send_slots(_policy(), 5, start_utc=start, slot_timezones=[MONTREAL] * 5)
    assert slots[0] == datetime(2026, 10, 12, 11, 0, 0)  # Monday 07:00 EDT
    assert all(_to_local(slot, MONTREAL).weekday() < 5 for slot in slots)

    paris_slots = send_policy_service.next_send_slots(_policy(), 1, start_utc=start)
    assert paris_slots == [datetime(2026, 10, 12, 5, 0, 0)]  # Monday 07:00 CEST


def test_fr_and_ca_campaigns_interleaved_respect_the_global_cap() -> None:
    """The cap counts the sender's day: a Montréal send occupies the Paris day it leaves on."""
    policy = _policy(daily_cap=2)
    start = datetime(2026, 10, 5, 5, 0, 0)  # Monday 07:00 Paris

    french = send_policy_service.next_send_slots(policy, 3, start_utc=start, per_campaign_cap=1)
    canadian = send_policy_service.next_send_slots(
        policy,
        3,
        start_utc=start,
        seed_counts=_sender_days(french),
        occupied=set(french),
        per_campaign_cap=1,
        slot_timezones=[MONTREAL] * 3,
    )

    combined = _sender_days(french + canadian)
    assert max(combined.values()) <= 2
    assert [_local(s).date() for s in french] == [_local(s).date() for s in canadian]
    assert set(french).isdisjoint(canadian)
    assert all(_to_local(slot, MONTREAL).hour == 7 for slot in canadian)


def test_canadian_sends_move_to_free_sender_days_when_the_cap_is_one() -> None:
    """With one send a day for the whole mailbox, the Montréal campaign waits for days France left free."""
    policy = _policy(daily_cap=1)
    start = datetime(2026, 10, 5, 5, 0, 0)  # Monday 07:00 Paris

    french = send_policy_service.next_send_slots(policy, 3, start_utc=start, per_campaign_cap=1)
    canadian = send_policy_service.next_send_slots(
        policy,
        3,
        start_utc=start,
        seed_counts=_sender_days(french),
        occupied=set(french),
        slot_timezones=[MONTREAL] * 3,
    )

    assert [_local(s).date() for s in french] == [date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 7)]
    assert [_local(s).date() for s in canadian] == [date(2026, 10, 8), date(2026, 10, 9), date(2026, 10, 12)]


def test_canadian_follow_up_keeps_the_local_hour_across_the_time_change() -> None:
    """A J1 at 8 a.m. in Montréal on the 26th answers at 8 a.m. in Montréal on the 2nd — 13:00 UTC, no longer 12:00."""
    sent_at = datetime(2026, 10, 26, 12, 0, 0)  # Monday 08:00 EDT
    follow_up = send_policy_service.follow_up_slot(_policy(), sent_at, timezone_name=MONTREAL)
    assert follow_up == datetime(2026, 11, 2, 13, 0, 0)
    assert _to_local(follow_up, MONTREAL) == datetime(2026, 11, 2, 8, 0, 0)


def test_follow_up_keeps_the_sender_hour_by_default() -> None:
    """Without a prospect zone the follow-up stays on the sender's clock, same weekday, same hour."""
    sent_at = datetime(2026, 10, 19, 12, 0, 0)  # Monday 14:00 CEST
    follow_up = send_policy_service.follow_up_slot(_policy(), sent_at)
    assert _local(follow_up) == datetime(2026, 10, 26, 14, 0, 0)  # Monday 14:00 CET


def test_slot_timezones_must_match_the_slot_count() -> None:
    """One zone per slot: a mismatch is a programming error, not something to guess around."""
    with pytest.raises(ValueError):
        send_policy_service.next_send_slots(_policy(), 2, slot_timezones=[MONTREAL])
