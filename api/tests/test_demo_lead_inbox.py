"""Demo-banner messages in the « à traiter » queues."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from models.demo_site_lead import LEAD_STATUS_SUBMITTED, DemoSiteLead
from models.prospect_db import ProspectDB
from services.demo_lead_inbox_service import demo_lead_inbox_service


def _prospect(db: Session, *, email: str | None, phone: str | None, country: str = "CH") -> ProspectDB:
    row = ProspectDB(
        user_id=7,
        name="Garage Test",
        city="Savièse",
        country=country,
        email=email,
        phone=phone,
        category="garage",
        source="manual",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _lead(db: Session, prospect_id: int, message: str = "Bonjour") -> DemoSiteLead:
    row = DemoSiteLead(
        user_id=7,
        prospect_id=prospect_id,
        demo_site_id=1,
        message=message,
        status=LEAD_STATUS_SUBMITTED,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_pending_routes_email_prospect_to_email_channel(db: Session) -> None:
    prospect = _prospect(db, email="garage@example.com", phone="+41765853113")
    _lead(db, prospect.id)
    email_items = demo_lead_inbox_service.pending_items(db, 7, "email")
    sms_items = demo_lead_inbox_service.pending_items(db, 7, "sms")
    assert len(email_items) == 1
    assert email_items[0]["source"] == "demo_lead"
    assert email_items[0]["preview"].startswith("Bonjour")
    assert sms_items == []


def test_pending_routes_sms_only_prospect_to_sms_channel(db: Session) -> None:
    prospect = _prospect(db, email=None, phone="+33642193812", country="FR")
    _lead(db, prospect.id, message="Intéressé")
    assert demo_lead_inbox_service.pending_items(db, 7, "email") == []
    sms_items = demo_lead_inbox_service.pending_items(db, 7, "sms")
    assert len(sms_items) == 1
    assert sms_items[0]["subject"] == "Message depuis la démo"


def test_mark_handled_for_prospect_clears_all(db: Session) -> None:
    prospect = _prospect(db, email="a@b.com", phone=None)
    lead = _lead(db, prospect.id)
    demo_lead_inbox_service.mark_handled_for_prospect(db, 7, prospect.id)
    db.refresh(lead)
    assert lead.handled_at is not None
    assert demo_lead_inbox_service.pending_items(db, 7, "email") == []
