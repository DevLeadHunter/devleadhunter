"""
« Écartés » — a prospect set aside stays in the base, so no search finds it again, but leaves every list,
campaign and enrichment until someone takes it back.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.v1.routes.enrichment import router as enrichment_router
from api.v1.routes.prospects import router as prospects_router
from core.database import get_db
from models.prospect_db import ProspectDB
from services.auth_service import get_current_active_user, require_auth
from services.campaign_queue_service import DISMISSED_SKIP_REASON, CampaignQueueService
from services.prospect_service import prospect_service
from services.sms_relance_service import sms_relance_service

_USER_ID = 1


def _prospect(db: Session, name: str) -> ProspectDB:
    """A prospect of the signed-in user."""
    prospect = ProspectDB(
        name=name,
        city="Morges",
        country="CH",
        category="paysagiste",
        source="search",
        confidence=3,
        user_id=_USER_ID,
    )
    db.add(prospect)
    db.commit()
    return prospect


def _client(db: Session) -> TestClient:
    """The prospect and enrichment routes, called by the signed-in user on the test database."""
    application = FastAPI()
    application.include_router(prospects_router)
    application.include_router(enrichment_router)
    signed_in_user: Any = SimpleNamespace(id=_USER_ID)
    application.dependency_overrides[require_auth] = lambda: signed_in_user
    application.dependency_overrides[get_current_active_user] = lambda: signed_in_user
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


def test_a_prospect_set_aside_by_the_app_leaves_the_list_with_its_reason(db: Session) -> None:
    """The register's closing sets the prospect aside: out of the list, listed with its reason and no author."""
    kept, closed = _prospect(db, "Exemple Jardins"), _prospect(db, "Modèle Paysages")

    prospect_service.dismiss(db, closed.id, reason="Entreprise radiée au registre", dismissed_by_user_id=None)

    client = _client(db)
    assert [prospect["id"] for prospect in client.get("/prospects").json()] == [kept.id]
    dismissed = client.get("/prospects/dismissed").json()
    assert [
        (prospect["id"], prospect["dismissal_reason"], prospect["dismissed_by_user_id"]) for prospect in dismissed
    ] == [(closed.id, "Entreprise radiée au registre", None)]


def test_a_member_sets_a_prospect_aside_then_takes_it_back(db: Session) -> None:
    """« Écarter » needs a reason; « Remettre » brings the prospect back to the list without one."""
    prospect = _prospect(db, "Exemple Jardins")
    client = _client(db)

    assert client.post(f"/prospects/{prospect.id}/dismissal", json={"reason": ""}).status_code == 422
    set_aside = client.post(f"/prospects/{prospect.id}/dismissal", json={"reason": "A déjà un site"}).json()
    assert (set_aside["dismissal_reason"], set_aside["dismissed_by_user_id"]) == ("A déjà un site", _USER_ID)
    assert client.get("/prospects").json() == []

    taken_back = client.delete(f"/prospects/{prospect.id}/dismissal").json()
    assert taken_back["dismissed_at"] is None and taken_back["dismissal_reason"] is None
    assert [listed["id"] for listed in client.get("/prospects").json()] == [prospect.id]
    assert client.get("/prospects/dismissed").json() == []


def test_a_prospect_set_aside_is_never_enriched_again(db: Session) -> None:
    """Enrichment refuses a prospect set aside, alone or in a batch, before any scraping."""
    prospect = _prospect(db, "Modèle Paysages")
    prospect_service.dismiss(db, prospect.id, reason="Entreprise radiée au registre", dismissed_by_user_id=None)
    client = _client(db)

    single = client.post(f"/prospects/{prospect.id}/enrichment/run")
    batch = client.post("/prospects/enrichment/bulk-run", json={"prospect_ids": [prospect.id]}).json()

    assert single.status_code == 409 and "écarté" in single.json()["detail"]
    assert (batch["failed"], batch["results"][0]["status"]) == (1, "failed")


def test_setting_aside_holds_back_the_pending_sends_with_the_reason() -> None:
    """The pending sends of a prospect set aside stay visible on the campaign, held back as « Écarté »."""
    pending = SimpleNamespace(id=1, prospect_id=7, status="pending", skip_reason=None)
    queue: Any = SimpleNamespace(
        query=lambda *_entities: queue, filter=lambda *_conditions: queue, all=lambda: [pending], commit=lambda: None
    )

    CampaignQueueService(queue).skip_pending_for_prospect(7, "fermé", label=DISMISSED_SKIP_REASON)

    assert (pending.status, pending.skip_reason) == ("skipped", "Écarté — fermé")


def test_a_prospect_set_aside_is_never_an_sms_candidate() -> None:
    """The automated SMS skip a prospect set aside, like one marked « ne plus contacter »."""
    prospect = SimpleNamespace(phone="06 12 34 56 78", do_not_contact=False, is_dismissed=True)

    candidate = sms_relance_service._build_candidate(None, user_id=1, prospect=prospect, emailed_at=None, cold=True)

    assert candidate is None
