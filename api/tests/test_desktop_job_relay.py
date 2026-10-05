"""Work asked from a tablet waits for the owner's desktop app, which takes it, does it and closes it."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import api.v1.routes.desktop_jobs as desktop_jobs_routes
from api.v1.routes.desktop_jobs import router as desktop_jobs_router
from core.database import get_db
from enums.desktop_job import DesktopJobKind, DesktopJobStatus
from enums.enrichment_status import EnrichmentStatus
from models.prospect_db import ProspectDB
from services.auth_service import require_auth
from services.desktop_job_relay import ALREADY_RUNNING_MESSAGE, NOT_WAITING_MESSAGE, DesktopJobRelay
from services.enrichment_service import enrichment_service
from services.prospect_search.desktop_app_presence import DesktopAppPresence

_USER_ID = 1
_OTHER_USER_ID = 2
_ENRICHMENT = DesktopJobKind.PROSPECT_ENRICHMENT


def _prospect(db: Session, name: str, user_id: int = _USER_ID) -> ProspectDB:
    prospect = ProspectDB(
        name=name,
        city="Limoges",
        country="FR",
        category="paysagiste",
        source="google",
        confidence=3,
        user_id=user_id,
        google_maps_url=f"https://maps.google.com/?q={name}",
    )
    db.add(prospect)
    db.commit()
    return prospect


def test_a_request_waits_for_the_desktop_app_with_what_the_scraper_needs(db: Session) -> None:
    relay = DesktopJobRelay()
    prospect = _prospect(db, "HB espace vert")

    job = relay.request(db, _USER_ID, _ENRICHMENT, prospect.id)

    assert job.status == DesktopJobStatus.WAITING.value
    assert job.payload["business_name"] == "HB espace vert"
    assert job.payload["city"] == "Limoges"
    assert job.payload["google_maps_url"] == prospect.google_maps_url
    assert job.payload["country"] == "FR"
    assert [waiting.id for waiting in relay.waiting_jobs(db, _USER_ID)] == [job.id]
    assert enrichment_service.get_for_prospect(db, _USER_ID, prospect.id).status == EnrichmentStatus.ENRICHING.value


def test_the_same_work_asked_twice_is_one_job(db: Session) -> None:
    relay = DesktopJobRelay()
    prospect = _prospect(db, "HB espace vert")

    first = relay.request(db, _USER_ID, _ENRICHMENT, prospect.id)
    second = relay.request(db, _USER_ID, _ENRICHMENT, prospect.id)

    assert second.id == first.id
    assert len(relay.active_jobs(db, _USER_ID)) == 1


def test_a_request_about_someone_else_s_prospect_is_refused(db: Session) -> None:
    prospect = _prospect(db, "Autre compte", user_id=_OTHER_USER_ID)

    with pytest.raises(ValueError):
        DesktopJobRelay().request(db, _USER_ID, _ENRICHMENT, prospect.id)


def test_the_desktop_app_gets_the_jobs_oldest_first_and_only_its_own(db: Session) -> None:
    relay = DesktopJobRelay()
    second = relay.request(db, _USER_ID, _ENRICHMENT, _prospect(db, "Second").id)
    first = relay.request(db, _USER_ID, _ENRICHMENT, _prospect(db, "Premier").id)
    relay.request(db, _OTHER_USER_ID, _ENRICHMENT, _prospect(db, "Autre", user_id=_OTHER_USER_ID).id)
    first.requested_at = first.requested_at - timedelta(hours=1)
    db.commit()

    assert [job.id for job in relay.waiting_jobs(db, _USER_ID)] == [first.id, second.id]


def test_a_claimed_job_is_not_offered_again_while_the_work_runs(db: Session) -> None:
    relay = DesktopJobRelay()
    job = relay.request(db, _USER_ID, _ENRICHMENT, _prospect(db, "HB espace vert").id)

    relay.claim(db, job)

    assert job.status == DesktopJobStatus.RUNNING.value
    assert relay.is_running(job) is True
    assert relay.waiting_jobs(db, _USER_ID) == []
    with pytest.raises(ValueError, match=ALREADY_RUNNING_MESSAGE):
        relay.claim(db, job)


def test_a_job_abandoned_by_a_closed_desktop_app_is_offered_again(db: Session) -> None:
    relay = DesktopJobRelay(claim_lifetime=timedelta(seconds=-1))
    job = relay.request(db, _USER_ID, _ENRICHMENT, _prospect(db, "HB espace vert").id)

    relay.claim(db, job)

    assert relay.is_running(job) is False
    assert [waiting.id for waiting in relay.waiting_jobs(db, _USER_ID)] == [job.id]
    relay.claim(db, job)
    assert job.status == DesktopJobStatus.RUNNING.value


def test_a_done_job_leaves_the_record_as_the_desktop_app_saved_it(db: Session) -> None:
    relay = DesktopJobRelay()
    prospect = _prospect(db, "HB espace vert")
    job = relay.request(db, _USER_ID, _ENRICHMENT, prospect.id)
    relay.claim(db, job)
    record = enrichment_service.get_or_create(db, _USER_ID, prospect.id)
    record.status = EnrichmentStatus.COMPLETED.value
    db.commit()

    relay.complete(db, job)

    assert job.status == DesktopJobStatus.DONE.value
    assert job.finished_at is not None
    assert record.status == EnrichmentStatus.COMPLETED.value
    assert relay.active_jobs(db, _USER_ID) == []
    with pytest.raises(ValueError, match=NOT_WAITING_MESSAGE):
        relay.complete(db, job)


def test_a_failure_marks_the_record_failed_with_its_reason(db: Session) -> None:
    relay = DesktopJobRelay()
    prospect = _prospect(db, "HB espace vert")
    job = relay.request(db, _USER_ID, _ENRICHMENT, prospect.id)
    relay.claim(db, job)

    relay.fail(db, job, "Le Chrome de ce poste ne répond plus.")

    record = enrichment_service.get_for_prospect(db, _USER_ID, prospect.id)
    assert job.status == DesktopJobStatus.FAILED.value
    assert job.error_message == "Le Chrome de ce poste ne répond plus."
    assert record.status == EnrichmentStatus.FAILED.value
    assert record.error_message == "Le Chrome de ce poste ne répond plus."


def test_a_cancelled_job_gives_the_record_back_its_previous_status(db: Session) -> None:
    relay = DesktopJobRelay()
    prospect = _prospect(db, "HB espace vert")
    record = enrichment_service.get_or_create(db, _USER_ID, prospect.id)
    record.status = EnrichmentStatus.COMPLETED.value
    db.commit()
    job = relay.request(db, _USER_ID, _ENRICHMENT, prospect.id)
    assert record.status == EnrichmentStatus.ENRICHING.value

    relay.cancel(db, job)

    assert job.status == DesktopJobStatus.CANCELLED.value
    assert record.status == EnrichmentStatus.COMPLETED.value
    assert relay.request(db, _USER_ID, _ENRICHMENT, prospect.id).id != job.id


def test_a_running_job_cannot_be_cancelled(db: Session) -> None:
    relay = DesktopJobRelay()
    job = relay.request(db, _USER_ID, _ENRICHMENT, _prospect(db, "HB espace vert").id)
    relay.claim(db, job)

    with pytest.raises(ValueError, match=ALREADY_RUNNING_MESSAGE):
        relay.cancel(db, job)


def _client(db: Session, user_id: int = _USER_ID) -> TestClient:
    """The desktop job routes, called by a signed-in user on the test database."""
    application = FastAPI()
    application.include_router(desktop_jobs_router)
    signed_in_user: Any = SimpleNamespace(id=user_id)
    application.dependency_overrides[require_auth] = lambda: signed_in_user
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


@pytest.fixture
def relay_routes(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """The routes on a fresh relay and a fresh desktop presence."""
    relay = DesktopJobRelay()
    presence = DesktopAppPresence()
    monkeypatch.setattr(desktop_jobs_routes, "desktop_job_relay", relay)
    monkeypatch.setattr(desktop_jobs_routes, "desktop_app_presence", presence)
    return SimpleNamespace(relay=relay, presence=presence)


def test_a_tablet_asks_and_the_desktop_app_takes_does_and_closes_the_job(
    db: Session, relay_routes: SimpleNamespace
) -> None:
    prospect = _prospect(db, "HB espace vert")
    client = _client(db)

    asked = client.post("/desktop-jobs", json={"kind": "prospect_enrichment", "subject_id": prospect.id})
    shown = client.get("/desktop-jobs", params={"kind": "prospect_enrichment", "subject_id": prospect.id})
    waiting = client.get("/desktop-jobs/waiting")
    job_id = asked.json()["id"]
    claimed = client.post(f"/desktop-jobs/{job_id}/claim")
    claimed_twice = client.post(f"/desktop-jobs/{job_id}/claim")
    done = client.post(f"/desktop-jobs/{job_id}/done")

    assert asked.status_code == 202
    assert asked.json()["payload"]["business_name"] == "HB espace vert"
    assert [job["id"] for job in shown.json()] == [job_id]
    assert [job["id"] for job in waiting.json()] == [job_id]
    assert relay_routes.presence.is_online(_USER_ID) is True
    assert claimed.status_code == 200
    assert claimed.json()["status"] == "running"
    assert claimed_twice.status_code == 409
    assert done.json()["status"] == "done"
    assert client.get("/desktop-jobs/waiting").json() == []


def test_a_tablet_withdraws_its_job_and_the_desktop_app_reports_why_it_gave_up(
    db: Session, relay_routes: SimpleNamespace
) -> None:
    client = _client(db)
    withdrawn_id = client.post(
        "/desktop-jobs", json={"kind": "prospect_enrichment", "subject_id": _prospect(db, "Premier").id}
    ).json()["id"]
    failed_id = client.post(
        "/desktop-jobs", json={"kind": "prospect_enrichment", "subject_id": _prospect(db, "Second").id}
    ).json()["id"]
    client.post(f"/desktop-jobs/{failed_id}/claim")

    withdrawn = client.delete(f"/desktop-jobs/{withdrawn_id}")
    withdrawn_twice = client.delete(f"/desktop-jobs/{withdrawn_id}")
    failed = client.post(f"/desktop-jobs/{failed_id}/fail", json={"message": "Chrome indisponible."})

    assert withdrawn.json()["status"] == "cancelled"
    assert withdrawn_twice.status_code == 409
    assert failed.json()["status"] == "failed"
    assert failed.json()["error_message"] == "Chrome indisponible."
    assert client.get("/desktop-jobs").json() == []


def test_another_account_cannot_reach_the_job(db: Session, relay_routes: SimpleNamespace) -> None:
    prospect = _prospect(db, "HB espace vert")
    job_id = (
        _client(db).post("/desktop-jobs", json={"kind": "prospect_enrichment", "subject_id": prospect.id}).json()["id"]
    )
    stranger = _client(db, user_id=_OTHER_USER_ID)

    assert stranger.get("/desktop-jobs/waiting").json() == []
    assert stranger.post(f"/desktop-jobs/{job_id}/claim").status_code == 404
    assert (
        stranger.post("/desktop-jobs", json={"kind": "prospect_enrichment", "subject_id": prospect.id}).status_code
        == 404
    )
