"""
Demo site lead model — a prospect raised their hand from their demo page.
"""

from datetime import datetime

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class DemoSiteLead(Base):
    """A lead left through the « Ce site vous plaît ? » banner on a live demo.

    Notifications are purged after ~90 days; the prospect's own words are business
    data worth keeping durably and attaching to the prospect, hence this table.

    Attributes:
        id: Unique identifier (auto-increment)
        user_id: Owner of the demo — who the lead belongs to
        prospect_id: Prospect the demo was generated for (nullable, follows the demo site)
        demo_site_id: Demo site the banner was submitted from
        message: Free text left by the prospect (may be empty — the click alone is the signal)
        created_at: Timestamp when the lead was submitted
    """

    __tablename__ = "demo_site_leads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    prospect_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    demo_site_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
