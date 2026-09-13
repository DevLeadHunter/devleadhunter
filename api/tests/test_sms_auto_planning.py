"""The auto-SMS planner assigns exact, capacity-aware slots.

``_assign_slots`` is the scheduling core behind the materialised queue: a relance is
placed on its first-email-plus-delay day (never dumped at "now"), the legal window and
the daily cap are honoured, and slots already taken by planned rows stay counted.
"""

import importlib
import pkgutil
from datetime import datetime, timedelta

from sqlalchemy.orm import configure_mappers

import models as _models_pkg

# Importing the service pulls in ORM models whose cross-relationships must resolve.
for _module in pkgutil.iter_modules(_models_pkg.__path__):
    importlib.import_module(f"models.{_module.name}")
configure_mappers()

import services.sms_automation_service as sas  # noqa: E402
from services.sms.send_window import is_within_window, now_in_paris  # noqa: E402

_service = sas.sms_automation_service


def test_future_relance_lands_on_its_eligibility_day():
    earliest = now_in_paris() + timedelta(days=15)

    slots = _service._assign_slots([earliest], slot_used={}, day_used={}, end_paris=now_in_paris() + timedelta(days=45))

    assert len(slots) == 1
    # On (or just after, window permitting) its email+delay day — never at "now".
    assert earliest <= slots[0] <= earliest + timedelta(days=4)
    assert is_within_window(slots[0])


def test_nothing_is_planned_past_the_horizon():
    earliest = now_in_paris() + timedelta(days=15)

    slots = _service._assign_slots([earliest], slot_used={}, day_used={}, end_paris=now_in_paris() + timedelta(days=2))

    assert slots == []


def test_daily_cap_spills_over_to_the_next_day():
    ready_now = now_in_paris()
    earliest_list = [ready_now] * 25

    slots = _service._assign_slots(
        earliest_list, slot_used={}, day_used={}, end_paris=now_in_paris() + timedelta(days=15)
    )

    assert len(slots) == 25
    per_day: dict[str, int] = {}
    for slot in slots:
        per_day[slot.date().isoformat()] = per_day.get(slot.date().isoformat(), 0) + 1
    assert all(count <= 20 for count in per_day.values())  # daily cap never exceeded
    assert len(per_day) >= 2  # 25 with a 20/day cap must spill onto a second day
    assert all(is_within_window(slot) for slot in slots)


def test_slots_already_planned_keep_their_capacity_reserved():
    ready_now = now_in_paris()
    # A prior planning pass filled today entirely: new entries must land on a later day.
    first_come = _service._assign_slots(
        [ready_now] * 20, slot_used={}, day_used={}, end_paris=now_in_paris() + timedelta(days=15)
    )
    day_used = {slot.date(): 0 for slot in first_come}
    slot_used: dict[datetime, int] = {}
    for slot in first_come:
        day_used[slot.date()] += 1
        slot_used[slot] = slot_used.get(slot, 0) + 1

    later = _service._assign_slots(
        [ready_now], slot_used=slot_used, day_used=day_used, end_paris=now_in_paris() + timedelta(days=15)
    )

    assert len(later) == 1
    assert later[0].date() > max(slot.date() for slot in first_come)
