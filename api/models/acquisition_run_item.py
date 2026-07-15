"""
AcquisitionRunItem model — one prospect flowing through a sequence.

Each item carries its own ``step`` so prospects advance independently and a
crash mid-run resumes exactly where it stopped.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from enums.acquisition import AcquisitionItemStep

if TYPE_CHECKING:
    from models.acquisition_run import AcquisitionRun


class AcquisitionRunItem(Base):
    """A single prospect's journey inside an :class:`AcquisitionRun`."""

    __tablename__ = "acquisition_run_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("acquisition_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prospect_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    step: Mapped[str] = mapped_column(
        String(24), nullable=False, default=AcquisitionItemStep.FOUND.value, index=True
    )
    # Human-readable reason for the current step (skip cause, quality flag…).
    step_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Demo-site template for THIS prospect (overrides the run default).
    template_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    demo_site_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Sellability triage: 0-100 score + the reasons it's flagged "à vérifier".
    quality_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quality_flags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now(), nullable=True)

    run: Mapped["AcquisitionRun"] = relationship("AcquisitionRun", back_populates="items")

    def __repr__(self) -> str:
        """String representation of the item."""
        return f"<AcquisitionRunItem id={self.id} prospect={self.prospect_id} step={self.step}>"
