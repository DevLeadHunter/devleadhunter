"""
« À traiter » queue for messages left on the demo CTA banner.

Routed by contact channel: prospects with an email join the email inbox;
SMS-only prospects join the SMS tracking page.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from models.demo_site_lead import LEAD_STATUS_SUBMITTED, DemoSiteLead
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from services.prospect_contact import prospect_demo_inbox_channel

DemoInboxChannel = Literal["email", "sms"]


class DemoLeadInboxService:
    """Pending demo leads and mark-as-handled."""

    @staticmethod
    def _pending_rows(db: Session, user_id: int) -> list[DemoSiteLead]:
        return list(
            db.execute(
                select(DemoSiteLead)
                .where(
                    DemoSiteLead.user_id == user_id,
                    DemoSiteLead.status == LEAD_STATUS_SUBMITTED,
                    DemoSiteLead.handled_at.is_(None),
                )
                .order_by(DemoSiteLead.id.desc())
            )
            .scalars()
            .all()
        )

    @staticmethod
    def _latest_email_log_id(db: Session, user_id: int, prospect_id: int | None) -> int | None:
        if not prospect_id:
            return None
        return db.execute(
            select(EmailLog.id)
            .where(EmailLog.user_id == user_id, EmailLog.prospect_id == prospect_id)
            .order_by(desc(EmailLog.id))
            .limit(1)
        ).scalar_one_or_none()

    def pending_items(self, db: Session, user_id: int, channel: DemoInboxChannel) -> list[dict[str, Any]]:
        rows = self._pending_rows(db, user_id)
        prospect_ids = [row.prospect_id for row in rows if row.prospect_id]
        prospects: dict[int, ProspectDB] = {}
        if prospect_ids:
            for prospect in db.execute(select(ProspectDB).where(ProspectDB.id.in_(prospect_ids))).scalars():
                prospects[prospect.id] = prospect

        items: list[dict[str, Any]] = []
        for lead in rows:
            prospect = prospects.get(lead.prospect_id or -1)
            if prospect_demo_inbox_channel(prospect) != channel:
                continue
            preview = (lead.message or "").strip() or "(intéressé — sans message)"
            received = lead.created_at
            items.append(
                {
                    "source": "demo_lead",
                    "id": lead.id,
                    "demo_lead_id": lead.id,
                    "email_log_id": self._latest_email_log_id(db, user_id, lead.prospect_id),
                    "prospect_id": lead.prospect_id,
                    "prospect_name": (prospect.name if prospect else None) or None,
                    "from_email": (prospect.email if prospect else "") or "",
                    "subject": "Message depuis la démo",
                    "preview": preview[:180],
                    "intent": None,
                    "received_at": received.isoformat() if received else None,
                }
            )
        return items

    @staticmethod
    def mark_handled(db: Session, user_id: int, lead_id: int) -> bool:
        lead: DemoSiteLead | None = db.get(DemoSiteLead, lead_id)
        if lead is None or lead.user_id != user_id:
            return False
        if lead.handled_at is None:
            lead.handled_at = datetime.now(UTC).replace(tzinfo=None)
            db.commit()
        return True

    @staticmethod
    def mark_handled_for_prospect(db: Session, user_id: int, prospect_id: int) -> None:
        """After a manual contact, clear every pending demo lead for this prospect."""
        rows = (
            db.execute(
                select(DemoSiteLead).where(
                    DemoSiteLead.user_id == user_id,
                    DemoSiteLead.prospect_id == prospect_id,
                    DemoSiteLead.status == LEAD_STATUS_SUBMITTED,
                    DemoSiteLead.handled_at.is_(None),
                )
            )
            .scalars()
            .all()
        )
        if not rows:
            return
        now = datetime.now(UTC).replace(tzinfo=None)
        for lead in rows:
            lead.handled_at = now
        db.commit()


demo_lead_inbox_service = DemoLeadInboxService()
