"""
AcquisitionRun model — one auto-chaining "sequence" over a batch of prospects.

A run is a *recipe*: what to prospect and how far to go automatically
(enrich → generate → review gate → campaign), plus guardrails (credit/email
caps).  The orchestrator (``acquisition_orchestrator``) advances its items one
step per tick; all state lives here in the DB so a restart resumes cleanly.
"""
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from enums.acquisition import AcquisitionRunMode, AcquisitionRunStatus

if TYPE_CHECKING:
    from models.acquisition_run_item import AcquisitionRunItem


class AcquisitionRun(Base):
    """A configured, resumable acquisition sequence scoped to a user/org."""

    __tablename__ = "acquisition_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    organization_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=AcquisitionRunStatus.DRAFT.value, index=True
    )
    mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default=AcquisitionRunMode.SEMI_AUTO.value
    )

    # --- Search config (reserved for Phase 2 "chain the search"; nullable now) ---
    search_category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    search_city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    search_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    max_results: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    only_without_website: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )

    # --- Step config: how far to go + with what ---
    auto_enrich: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    auto_generate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    template_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # demo-site template
    auto_campaign: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    email_template_id_a: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    email_template_id_b: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    send_delay_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=20, server_default="20")
    # Optional follow-up steps: list of {"template_id": int, "delay_days": int}.
    follow_ups: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # --- Guardrails ---
    max_credits: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    daily_email_cap: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # --- Linkage & tracking ---
    campaign_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    review_approved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    stats: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now(), nullable=True)

    items: Mapped[List["AcquisitionRunItem"]] = relationship(
        "AcquisitionRunItem",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AcquisitionRunItem.id",
    )

    def __repr__(self) -> str:
        """String representation of the run."""
        return f"<AcquisitionRun id={self.id} status={self.status} mode={self.mode}>"
