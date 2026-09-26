"""
Demo site lead model — a prospect raised their hand from their demo page.
"""

from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base

LEAD_STATUS_SUBMITTED = "submitted"
LEAD_STATUS_DRAFT = "draft"


class DemoSiteLead(Base):
    """A lead left through the « Ce site vous plaît ? » banner on a live demo.

    Notifications are purged after ~90 days; the prospect's own words are business
    data worth keeping durably and attaching to the prospect, hence this table.

    Two kinds share the table, told apart by ``status``: a ``submitted`` lead (the
    prospect clicked « Je suis intéressé ») and a ``draft`` — a message they typed
    then left without sending. The draft is captured so their words are never lost,
    but kept distinct so it never counts as a real hand-raise in lead scoring.

    Attributes:
        id: Unique identifier (auto-increment)
        user_id: Owner of the demo — who the lead belongs to
        prospect_id: Prospect the demo was generated for (nullable, follows the demo site)
        demo_site_id: Demo site the banner was submitted from
        message: Free text left by the prospect (may be empty — the click alone is the signal)
        status: ``submitted`` (real lead) or ``draft`` (typed then abandoned without sending)
        created_at: Timestamp when the lead was submitted
        updated_at: Last time the row changed — a draft is upserted as the prospect keeps typing
    """

    __tablename__ = "demo_site_leads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    prospect_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    demo_site_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=LEAD_STATUS_SUBMITTED, server_default=LEAD_STATUS_SUBMITTED, index=True
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.utcnow, nullable=True)
