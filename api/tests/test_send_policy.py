"""
Unit tests for the send-policy slot scheduler.

These assert structural invariants (window, weekdays, spacing, daily cap) in
policy-local time, so they hold whether or not the timezone database is present.
"""
from datetime import datetime

from services.send_policy_service import ResolvedPolicy, _to_local, send_policy_service


def _local(dt: datetime) -> datetime:
    """Convert a returned naive-UTC slot to policy-local time for assertions."""
    return _to_local(dt)


def _policy() -> ResolvedPolicy:
    """A Mon–Fri, 07:00–18:00, 1/20min, 20/day policy."""
    return ResolvedPolicy(
        daily_cap=20,
        days_of_week=[0, 1, 2, 3, 4],
        window_start_hour=7,
        window_end_hour=18,
        spacing_minutes=20,
    )


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
    """No local calendar day exceeds the daily cap."""
    policy = ResolvedPolicy(5, [0, 1, 2, 3, 4], 7, 18, 20)
    slots = send_policy_service.next_send_slots(policy, 23)
    per_day: dict[object, int] = {}
    for slot in slots:
        day = _local(slot).date()
        per_day[day] = per_day.get(day, 0) + 1
    assert max(per_day.values()) <= 5
    # 23 items at 5/day → spread over at least 5 days.
    assert len(per_day) >= 5


def test_spacing_within_day() -> None:
    """Two slots on the same local day are at least ``spacing_minutes`` apart."""
    policy = _policy()
    slots = send_policy_service.next_send_slots(policy, 10)
    for earlier, later in zip(slots, slots[1:]):
        le, ll = _local(earlier), _local(later)
        if le.date() == ll.date():
            assert (ll - le).total_seconds() >= policy.spacing_minutes * 60 - 1


def test_seed_counts_pushes_to_next_day() -> None:
    """A day already at the cap gets no new slots."""
    policy = ResolvedPolicy(3, [0, 1, 2, 3, 4], 7, 18, 20)
    start = datetime(2026, 7, 13, 6, 0, 0)  # Monday, before the window (UTC)
    first_local_day = _to_local(start).date()
    slots = send_policy_service.next_send_slots(
        policy, 3, start_utc=start, seed_counts={first_local_day: 3}
    )
    assert all(_local(s).date() != first_local_day for s in slots)
