"""No campaign email reaches a prospect on one of his public holidays: its slot moves to his next sending day.

Wednesday the 11th of November 2026 is a holiday in France and in Martinique, a working day in Switzerland. A first
email due that day leaves on the 12th for a French or a Martinique prospect and on the 11th for a Swiss one, a relance
counted in sending days does not count the 11th in France, and August 1st is skipped for a Swiss prospect only. The
launch, the resume after a pause, the relance, « Renvoyer », the re-plan after a network cut and the bounce fallback
all place their slot on the prospect's calendar, and the forecast shows it. The policy sends Monday to Friday, from
8 a.m. to 6 p.m. on the prospect's clock, and relances three sending days after the first email.
"""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import services.campaign_queue_service as campaign_queue_module
import services.send_policy_service as send_policy_module
from api.v1.routes.campaigns import router as campaigns_router
from core.database import get_db
from models.campaign import Campaign, CampaignStatus, campaign_prospects
from models.campaign_follow_up import CampaignFollowUp
from models.email_queue import EmailQueue
from models.email_template import EmailTemplate
from models.prospect_db import ProspectDB
from models.resend_config import ResendConfig
from models.send_policy import SendPolicy
from services.auth_service import get_current_user
from services.bounce_fallback_service import BounceFallbackService
from services.campaign_queue_service import CampaignQueueService
from services.prospect_calendar import ProspectCalendar
from services.prospect_timezone import prospect_timezone
from services.send_policy_service import ResolvedPolicy, _to_local, send_policy_service

_USER_ID = 7
_TUESDAY_10TH_EVENING_UTC = datetime(2026, 11, 10, 22, 0)
_MONDAY_9TH_AT_TEN_IN_PARIS_UTC = datetime(2026, 11, 9, 9, 0)
_NETWORK_FAILURE = {"success": False, "error": "Resend injoignable après 4 essais", "error_kind": "network"}

_PARIS = ProspectCalendar(timezone_name="Europe/Paris", country="FR")
_FORT_DE_FRANCE = ProspectCalendar(timezone_name="America/Martinique", country="FR", region="MQ")
_ZURICH = ProspectCalendar(timezone_name="Europe/Zurich", country="CH")


def _policy() -> ResolvedPolicy:
    """Monday to Friday, 8 a.m. to 6 p.m. on the prospect's clock, a relance three sending days later."""
    return ResolvedPolicy(
        daily_cap=20,
        days_of_week=[0, 1, 2, 3, 4],
        window_start_hour=8,
        window_end_hour=18,
        spacing_minutes=20,
        follow_up_delay_days=3,
    )


def _first_slot(start_utc: datetime, calendar: ProspectCalendar) -> datetime:
    """The first send slot from *start_utc*, read on the prospect's clock."""
    slot = send_policy_service.next_send_slots(_policy(), 1, start_utc=start_utc, slot_calendars=[calendar])[0]
    return _to_local(slot, calendar.timezone_name)


def _freeze_clock(monkeypatch: pytest.MonkeyPatch, now_utc: datetime) -> None:
    """Set the « now » of the queue and of the scheduler."""
    monkeypatch.setattr(campaign_queue_module, "_utcnow", lambda: now_utc)
    monkeypatch.setattr(send_policy_module, "_utcnow", lambda: now_utc)


@pytest.fixture
def sending_setup(db: Session) -> None:
    """The user's send policy and his Resend identity."""
    db.add(
        SendPolicy(
            user_id=_USER_ID,
            daily_cap=20,
            days_of_week=[0, 1, 2, 3, 4],
            window_start_hour=8,
            window_end_hour=18,
            spacing_minutes=20,
            follow_up_delay_days=3,
        )
    )
    db.add(ResendConfig(user_id=_USER_ID, api_key="re_test", from_email="leo@mail.example.com"))
    db.commit()


def _prospect(db: Session, name: str, *, country: str, address: str) -> ProspectDB:
    prospect = ProspectDB(
        name=name,
        category="plombier",
        source="google",
        confidence=2,
        user_id=_USER_ID,
        country=country,
        address=address,
        email=f"{name.lower().replace(' ', '.')}@example.com",
    )
    db.add(prospect)
    db.commit()
    return prospect


def _swiss_prospect(db: Session) -> ProspectDB:
    return _prospect(db, "Sanitaires Leman", country="CH", address="Rue du Rhône 12, 1204 Genève")


def _french_prospect(db: Session) -> ProspectDB:
    return _prospect(db, "Plomberie Blois", country="FR", address="12 Rue Nationale, 41000 Blois")


def _martinique_prospect(db: Session) -> ProspectDB:
    return _prospect(db, "Plomberie Lamentin", country="FR", address="Zi la Lézarde, Le Lamentin 97232, Martinique")


def _campaign(db: Session, prospects: list[ProspectDB]) -> Campaign:
    """A draft email campaign whose plain first email needs no demo, its prospects in the given send order."""
    template = EmailTemplate(user_id=_USER_ID, name="Premier contact", subject="votre site", body_html="<p>Bonjour</p>")
    db.add(template)
    db.flush()
    campaign = Campaign(
        user_id=_USER_ID, name="Vague 5", status=CampaignStatus.DRAFT, channel="email", template_id=template.id
    )
    db.add(campaign)
    db.flush()
    for position, prospect in enumerate(prospects):
        db.execute(
            campaign_prospects.insert().values(campaign_id=campaign.id, prospect_id=prospect.id, position=position)
        )
    db.commit()
    return campaign


def _client(db: Session) -> TestClient:
    """The campaign routes, called by the signed-in user on the test database."""
    application = FastAPI()
    application.include_router(campaigns_router)
    signed_in_user: Any = SimpleNamespace(id=_USER_ID)
    application.dependency_overrides[get_current_user] = lambda: signed_in_user
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


def _pending_first_email(db: Session, prospect: ProspectDB) -> EmailQueue:
    return (
        db.query(EmailQueue)
        .filter(
            EmailQueue.prospect_id == prospect.id,
            EmailQueue.queue_type == "initial",
            EmailQueue.status == "pending",
        )
        .one()
    )


def _on_his_clock(moment_utc: datetime, prospect: ProspectDB) -> datetime:
    return _to_local(moment_utc, prospect_timezone(prospect))


def _launch(db: Session, campaign: Campaign) -> int:
    """
    Activate a campaign and fill its send queue, what « Lancer » and « Reprendre » do.

    The routes are not called: they write the status as a raw value the test database's enum column refuses.
    """
    campaign.status = CampaignStatus.ACTIVE
    db.commit()
    return CampaignQueueService(db).enqueue_campaign(campaign, template_id=campaign.template_id).enqueued


def _pause(db: Session, campaign: Campaign) -> None:
    """Hold a campaign back, what « Pause » does: its pending sends are cancelled."""
    campaign.status = CampaignStatus.PAUSED
    db.commit()
    CampaignQueueService(db).cancel_campaign_queue(campaign.id)


def _launch_on_the_evening_of_the_10th(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> tuple[ProspectDB, ProspectDB, ProspectDB]:
    """Launch a campaign to a Swiss, a French and a Martinique prospect, in this order, on Tuesday evening."""
    _freeze_clock(monkeypatch, _TUESDAY_10TH_EVENING_UTC)
    swiss, french, martiniquais = _swiss_prospect(db), _french_prospect(db), _martinique_prospect(db)

    assert _launch(db, _campaign(db, [swiss, french, martiniquais])) == 3
    return swiss, french, martiniquais


def test_a_first_email_due_on_november_11th_leaves_on_the_12th_for_a_french_or_martinique_prospect() -> None:
    assert _first_slot(_TUESDAY_10TH_EVENING_UTC, _PARIS) == datetime(2026, 11, 12, 8, 0)
    assert _first_slot(_TUESDAY_10TH_EVENING_UTC, _FORT_DE_FRANCE) == datetime(2026, 11, 12, 8, 0)


def test_a_first_email_due_on_november_11th_leaves_that_day_for_a_swiss_prospect() -> None:
    assert _first_slot(_TUESDAY_10TH_EVENING_UTC, _ZURICH) == datetime(2026, 11, 11, 8, 0)


def test_a_relance_three_sending_days_after_a_monday_does_not_count_november_11th_in_france() -> None:
    french = send_policy_service.follow_up_slot(_policy(), _MONDAY_9TH_AT_TEN_IN_PARIS_UTC, calendar=_PARIS)
    swiss = send_policy_service.follow_up_slot(_policy(), _MONDAY_9TH_AT_TEN_IN_PARIS_UTC, calendar=_ZURICH)

    assert _to_local(french, _PARIS.timezone_name) == datetime(2026, 11, 13, 10, 0)
    assert _to_local(swiss, _ZURICH.timezone_name) == datetime(2026, 11, 12, 10, 0)


def test_august_1st_is_skipped_for_a_swiss_prospect_and_kept_for_a_french_one() -> None:
    friday_august_1st_2025_at_dawn_utc = datetime(2025, 8, 1, 4, 0)

    assert _first_slot(friday_august_1st_2025_at_dawn_utc, _ZURICH) == datetime(2025, 8, 4, 8, 0)
    assert _first_slot(friday_august_1st_2025_at_dawn_utc, _PARIS) == datetime(2025, 8, 1, 8, 0)


def test_a_martinique_prospect_is_also_spared_the_day_his_island_commemorates_the_abolition_of_slavery() -> None:
    friday_may_22nd_2026_at_dawn_utc = datetime(2026, 5, 22, 4, 0)

    assert _first_slot(friday_may_22nd_2026_at_dawn_utc, _PARIS) == datetime(2026, 5, 22, 8, 0)
    assert _first_slot(friday_may_22nd_2026_at_dawn_utc, _FORT_DE_FRANCE) == datetime(2026, 5, 26, 8, 0)


def test_without_a_prospect_the_sender_calendar_keeps_the_french_holidays() -> None:
    slot = send_policy_service.advance_into_window(datetime(2026, 11, 11, 9, 0), _policy())

    assert _to_local(slot, _PARIS.timezone_name) == datetime(2026, 11, 12, 8, 0)


def test_a_launch_on_the_evening_of_the_10th_emails_switzerland_on_the_11th_and_france_and_martinique_on_the_12th(
    db: Session, sending_setup: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    swiss, french, martiniquais = _launch_on_the_evening_of_the_10th(db, monkeypatch)

    assert [
        _on_his_clock(_pending_first_email(db, prospect).scheduled_at, prospect)
        for prospect in (swiss, french, martiniquais)
    ] == [datetime(2026, 11, 11, 8, 0), datetime(2026, 11, 12, 8, 0), datetime(2026, 11, 12, 8, 0)]


def test_the_forecast_shows_the_french_and_martinique_first_emails_on_the_12th(
    db: Session, sending_setup: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    swiss, french, martiniquais = _launch_on_the_evening_of_the_10th(db, monkeypatch)

    response = _client(db).get(f"{campaigns_router.prefix}/forecast", params={"start": "2026-11-09T00:00:00Z"})

    days_by_prospect = {
        item["prospect_id"]: _to_local(datetime.fromisoformat(item["scheduled_at"]), item["prospect_timezone"]).date()
        for item in response.json()["items"]
    }
    assert days_by_prospect == {
        swiss.id: date(2026, 11, 11),
        french.id: date(2026, 11, 12),
        martiniquais.id: date(2026, 11, 12),
    }


def test_a_campaign_resumed_on_the_evening_of_the_10th_replans_its_cancelled_first_email_for_the_12th(
    db: Session, sending_setup: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    french = _french_prospect(db)
    campaign = _campaign(db, [french])
    _freeze_clock(monkeypatch, datetime(2026, 11, 9, 20, 0))
    _launch(db, campaign)
    planned_for_tuesday = _on_his_clock(_pending_first_email(db, french).scheduled_at, french)
    _pause(db, campaign)

    _freeze_clock(monkeypatch, _TUESDAY_10TH_EVENING_UTC)
    resumed = _launch(db, campaign)

    assert planned_for_tuesday == datetime(2026, 11, 10, 8, 0)
    assert resumed == 1
    assert _on_his_clock(_pending_first_email(db, french).scheduled_at, french) == datetime(2026, 11, 12, 8, 0)


def test_renvoyer_on_the_evening_of_the_10th_waits_for_the_next_day_the_prospect_works(
    db: Session, sending_setup: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    swiss, martiniquais = _swiss_prospect(db), _martinique_prospect(db)
    campaign = _campaign(db, [swiss, martiniquais])
    campaign.status = CampaignStatus.ACTIVE
    failed_sends = [
        EmailQueue(
            user_id=_USER_ID,
            campaign_id=campaign.id,
            prospect_id=prospect.id,
            template_id=campaign.template_id,
            queue_type="initial",
            scheduled_at=datetime(2026, 11, 10, 13, 0),
            status="failed",
        )
        for prospect in (swiss, martiniquais)
    ]
    db.add_all(failed_sends)
    db.commit()
    _freeze_clock(monkeypatch, _TUESDAY_10TH_EVENING_UTC)
    client = _client(db)

    for failed_send in failed_sends:
        response = client.post(f"{campaigns_router.prefix}/{campaign.id}/queue/{failed_send.id}/resend")
        assert response.status_code == 200

    assert _on_his_clock(_pending_first_email(db, swiss).scheduled_at, swiss) == datetime(2026, 11, 11, 8, 0)
    assert _on_his_clock(_pending_first_email(db, martiniquais).scheduled_at, martiniquais) == datetime(
        2026, 11, 12, 8, 0
    )


def test_a_relance_planned_after_a_monday_first_email_skips_november_11th_for_the_french_prospect_only(
    db: Session, sending_setup: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    swiss, french = _swiss_prospect(db), _french_prospect(db)
    campaign = _campaign(db, [swiss, french])
    db.add(CampaignFollowUp(campaign_id=campaign.id, template_id=campaign.template_id, delay_days=3, position=1))
    first_emails = [
        EmailQueue(
            user_id=_USER_ID,
            campaign_id=campaign.id,
            prospect_id=prospect.id,
            template_id=campaign.template_id,
            queue_type="initial",
            scheduled_at=_MONDAY_9TH_AT_TEN_IN_PARIS_UTC,
            status="sent",
        )
        for prospect in (swiss, french)
    ]
    db.add_all(first_emails)
    db.commit()
    _freeze_clock(monkeypatch, _MONDAY_9TH_AT_TEN_IN_PARIS_UTC)

    for first_email in first_emails:
        CampaignQueueService(db)._schedule_follow_ups(first_email)

    relance_by_prospect = {
        relance.prospect_id: relance.scheduled_at
        for relance in db.query(EmailQueue).filter(EmailQueue.queue_type == "followup")
    }
    assert _on_his_clock(relance_by_prospect[swiss.id], swiss) == datetime(2026, 11, 12, 10, 0)
    assert _on_his_clock(relance_by_prospect[french.id], french) == datetime(2026, 11, 13, 10, 0)


@pytest.mark.asyncio
async def test_a_network_cut_on_the_evening_of_the_10th_replans_a_martinique_email_for_the_12th(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_clock(monkeypatch, _TUESDAY_10TH_EVENING_UTC)
    monkeypatch.setattr(send_policy_service, "resolve", lambda db, user_id: _policy())
    item = SimpleNamespace(id=7, user_id=_USER_ID, status="sending", scheduled_at=None, send_attempts=0)
    martiniquais = SimpleNamespace(
        id=1, name="Plomberie Lamentin", country="FR", address="Le Lamentin 97232, Martinique", phones=[], phone=None
    )

    await CampaignQueueService(SimpleNamespace(commit=lambda: None))._settle_failed_send(
        item, martiniquais, _NETWORK_FAILURE
    )

    assert item.status == "pending"
    assert _to_local(item.scheduled_at, _FORT_DE_FRANCE.timezone_name) == datetime(2026, 11, 12, 8, 0)


def test_a_bounce_fallback_on_the_evening_of_the_10th_waits_for_the_12th_in_france(
    db: Session, sending_setup: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _freeze_clock(monkeypatch, _TUESDAY_10TH_EVENING_UTC)

    slot = BounceFallbackService._next_slot(db, _USER_ID, _PARIS)

    assert _to_local(slot, _PARIS.timezone_name) == datetime(2026, 11, 12, 8, 0)
