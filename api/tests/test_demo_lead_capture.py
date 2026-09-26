"""Unsent-draft capture: a message typed into the « Ce site vous plaît ? » banner
then abandoned is persisted as a ``draft`` lead — kept, upserted, and never counted
as a real hand-raise in lead scoring."""

from types import SimpleNamespace

from sqlalchemy.orm import Session

from api.v1.routes.demo_events import _persist_draft, _persist_submitted_lead
from models.demo_site_lead import LEAD_STATUS_DRAFT, LEAD_STATUS_SUBMITTED, DemoSiteLead
from services.behavior_service import behavior_service


def _site() -> SimpleNamespace:
    """A minimal demo-site stand-in carrying only what the persist helpers read."""
    return SimpleNamespace(id=1, user_id=7, prospect_id=42, slug="grg-chauffage")


def test_draft_is_persisted(db: Session) -> None:
    _persist_draft(db, _site(), "je suis intéressé mais j'ai une question")
    rows = db.query(DemoSiteLead).all()
    assert len(rows) == 1
    assert rows[0].status == LEAD_STATUS_DRAFT
    assert rows[0].message == "je suis intéressé mais j'ai une question"
    assert rows[0].prospect_id == 42


def test_draft_is_upserted_not_duplicated(db: Session) -> None:
    site = _site()
    _persist_draft(db, site, "bonjour")
    _persist_draft(db, site, "bonjour, c'est combien exactement ?")
    rows = db.query(DemoSiteLead).all()
    assert len(rows) == 1
    assert rows[0].message == "bonjour, c'est combien exactement ?"


def test_draft_never_touches_a_submitted_lead(db: Session) -> None:
    site = _site()
    _persist_submitted_lead(db, site, "je prends")
    _persist_draft(db, site, "un brouillon")
    rows = db.query(DemoSiteLead).order_by(DemoSiteLead.id).all()
    assert len(rows) == 2
    assert rows[0].status == LEAD_STATUS_SUBMITTED
    assert rows[0].message == "je prends"
    assert rows[1].status == LEAD_STATUS_DRAFT


def test_scoring_ignores_drafts_but_counts_submissions(db: Session) -> None:
    site = _site()
    _persist_draft(db, site, "juste un brouillon")
    assert behavior_service._demo_leads_count_bulk(db, 7, [42]).get(42, 0) == 0
    assert behavior_service._demo_leads(db, 7, 42) == []

    _persist_submitted_lead(db, site, "je prends")
    assert behavior_service._demo_leads_count_bulk(db, 7, [42]).get(42) == 1
    assert len(behavior_service._demo_leads(db, 7, 42)) == 1
