"""A Martinique prospect, French in every other respect, receives his emails between 8 a.m. and 6 p.m. in Fort-de-France.

Martinique (``America/Martinique``) lives at UTC−4 all year: five hours behind Paris once Paris is on winter
time (from the 25th of October 2026). Its prospects keep ``country = "FR"``; their clock is read from the
postal code of their address (972xx), else from the department named at its end, else from their number.
A mainland prospect stays on Paris time.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import services.campaign_queue_service as campaign_queue_module
from services.campaign_queue_service import CampaignQueueService
from services.prospect_timezone import prospect_timezone
from services.send_policy_service import ResolvedPolicy, _to_local, send_policy_service

MARTINIQUE: str = "America/Martinique"
PARIS: str = "Europe/Paris"
# Monday the 2nd of November 2026, 05:00 UTC: 06:00 in Paris, 01:00 in Fort-de-France.
MONDAY_DAWN_UTC: datetime = datetime(2026, 11, 2, 5, 0)


def _prospect(prospect_id: int, *, address: str | None, phone: str | None = None) -> SimpleNamespace:
    """A French prospect as the queue reads it."""
    return SimpleNamespace(id=prospect_id, country="FR", address=address, phones=[phone] if phone else [], phone=phone)


def _martinique_prospect(prospect_id: int) -> SimpleNamespace:
    return _prospect(prospect_id, address="Zi la Lézarde, Le Lamentin 97232, Martinique", phone="+596 696 04 04 25")


def _mainland_prospect(prospect_id: int) -> SimpleNamespace:
    return _prospect(prospect_id, address="12 Rue Nationale, 41000 Blois", phone="06 12 34 56 78")


def _eight_to_six_policy() -> ResolvedPolicy:
    """Monday to Friday, 08:00 to 18:00 on the prospect's clock, one email every 20 minutes."""
    return ResolvedPolicy(
        daily_cap=20,
        days_of_week=[0, 1, 2, 3, 4],
        window_start_hour=8,
        window_end_hour=18,
        spacing_minutes=20,
        follow_up_delay_days=3,
    )


def _is_inside_eight_to_six(moment_utc: datetime, timezone_name: str) -> bool:
    local = _to_local(moment_utc, timezone_name)
    return local.weekday() < 5 and 8 <= local.hour < 18


class _FakeDB:
    """Session stand-in answering the follow-up query with the campaign's steps, recording the rows added."""

    def __init__(self, steps: list[object] | None = None) -> None:
        self._steps = list(steps or [])
        self.added: list[object] = []

    def execute(self, *args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: list(self._steps)))

    def add(self, row: object) -> None:
        self.added.append(row)

    def commit(self) -> None:
        return None


@pytest.fixture
def eight_to_six(monkeypatch: pytest.MonkeyPatch) -> None:
    """The user's send policy is 8 a.m. to 6 p.m., no email is queued yet."""
    monkeypatch.setattr(send_policy_service, "get_policy", lambda db, user_id: object())
    monkeypatch.setattr(send_policy_service, "resolve", lambda db, user_id: _eight_to_six_policy())
    monkeypatch.setattr(send_policy_service, "pending_schedule", lambda db, user_id: ({}, set()))
    monkeypatch.setattr(send_policy_service, "pending_campaign_counts_by_day", lambda db, campaign_id: {})


def test_a_972_prospect_reads_the_martinique_clock_and_a_mainland_one_paris() -> None:
    assert prospect_timezone(_martinique_prospect(1)) == MARTINIQUE
    assert prospect_timezone(_mainland_prospect(2)) == PARIS
    assert CampaignQueueService.prospect_timezone(_martinique_prospect(1)) == MARTINIQUE


def test_without_postal_code_the_department_named_at_the_end_or_the_number_tells_the_clock() -> None:
    named_at_the_end = _prospect(1, address="35 Imp. Jacinthe, Le Lamentin, Martinique")
    by_number_only = _prospect(2, address=None, phone="05 96 51 62 52")

    assert prospect_timezone(named_at_the_end) == MARTINIQUE
    assert prospect_timezone(by_number_only) == MARTINIQUE


def test_a_mainland_address_keeps_paris_time_even_with_a_martinique_mobile() -> None:
    moved_from_martinique = _prospect(1, address="12 Rue Nationale, 41000 Blois", phone="0696 04 04 25")

    assert prospect_timezone(moved_from_martinique) == PARIS


def test_the_other_overseas_departments_read_their_own_clock() -> None:
    assert prospect_timezone(_prospect(1, address="Rue Schoelcher, 97110 Pointe-à-Pitre")) == "America/Guadeloupe"
    assert prospect_timezone(_prospect(2, address="Avenue de Cayenne, 97300 Cayenne")) == "America/Cayenne"
    assert prospect_timezone(_prospect(3, address="Rue de Paris, 97400 Saint-Denis")) == "Indian/Reunion"
    assert prospect_timezone(_prospect(4, address="Rue du Commerce, 97600 Mamoudzou")) == "Indian/Mayotte"


def test_a_foreign_prospect_keeps_his_country_clock() -> None:
    swiss = SimpleNamespace(id=1, country="CH", address="Rue du Rhône 12, 1204 Genève", phones=[], phone=None)

    assert prospect_timezone(swiss) == "Europe/Zurich"
    assert prospect_timezone(None) == PARIS


def test_first_emails_leave_between_eight_and_six_in_fort_de_france_and_mainland_stays_on_paris_time(
    eight_to_six: None,
) -> None:
    campaign = SimpleNamespace(id=6, user_id=1, max_emails_per_day=None, send_delay_minutes=20)
    prospects = [_martinique_prospect(1), _mainland_prospect(2), _martinique_prospect(3), _mainland_prospect(4)]

    slots = CampaignQueueService(_FakeDB())._schedule_slots(campaign, prospects, MONDAY_DAWN_UTC, None)

    zones = [MARTINIQUE, PARIS, MARTINIQUE, PARIS]
    assert all(_is_inside_eight_to_six(slot, zone) for slot, zone in zip(slots, zones, strict=True))
    assert slots[0] == datetime(2026, 11, 2, 12, 0)
    assert _to_local(slots[0], MARTINIQUE) == datetime(2026, 11, 2, 8, 0)
    assert _to_local(slots[0], PARIS) == datetime(2026, 11, 2, 13, 0)


def test_a_mainland_campaign_alone_still_starts_at_eight_in_paris(eight_to_six: None) -> None:
    campaign = SimpleNamespace(id=6, user_id=1, max_emails_per_day=None, send_delay_minutes=20)

    slots = CampaignQueueService(_FakeDB())._schedule_slots(campaign, [_mainland_prospect(2)], MONDAY_DAWN_UTC, None)

    assert slots == [datetime(2026, 11, 2, 7, 0)]
    assert _to_local(slots[0], PARIS) == datetime(2026, 11, 2, 8, 0)


def test_a_martinique_follow_up_leaves_at_the_local_hour_of_its_first_email(
    eight_to_six: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent_at = datetime(2026, 11, 2, 12, 0)  # Monday 08:00 in Fort-de-France
    monkeypatch.setattr(campaign_queue_module, "_utcnow", lambda: sent_at)
    campaign = SimpleNamespace(id=6, user_id=1, follow_up_template_id=None)
    step = SimpleNamespace(template_id=44, sms_template_key=None, delay_days=3, position=1)
    j1_item = SimpleNamespace(
        id=1,
        user_id=1,
        campaign_id=6,
        prospect_id=1,
        ab_variant=None,
        campaign=campaign,
        prospect=_martinique_prospect(1),
    )
    db = _FakeDB([step])
    service = CampaignQueueService(db)
    service._offer_link_outlives = lambda item, scheduled_at, **template: True  # type: ignore[method-assign]

    service._schedule_follow_ups(j1_item)

    follow_up_at = db.added[0].scheduled_at
    assert _to_local(follow_up_at, MARTINIQUE) == datetime(2026, 11, 5, 8, 0)  # Thursday 08:00 in Fort-de-France
    assert _is_inside_eight_to_six(follow_up_at, MARTINIQUE)


def test_a_martinique_email_re_sent_at_night_waits_for_eight_in_fort_de_france(
    eight_to_six: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    night_in_martinique = datetime(2026, 11, 3, 23, 30)  # Tuesday 19:30 in Fort-de-France, past the window
    monkeypatch.setattr(campaign_queue_module, "_utcnow", lambda: night_in_martinique)
    item = SimpleNamespace(id=9, user_id=1, status="failed", skip_reason=None, prospect=_martinique_prospect(1))

    CampaignQueueService(_FakeDB()).requeue_item(item)  # type: ignore[arg-type]

    assert item.status == "pending"
    assert _to_local(item.scheduled_at, MARTINIQUE) == datetime(2026, 11, 4, 8, 0)
    assert item.scheduled_at - night_in_martinique < timedelta(hours=13)
