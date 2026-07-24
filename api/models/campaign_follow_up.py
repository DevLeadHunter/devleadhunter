"""
CampaignFollowUp model — ordered list of follow-up emails for a campaign.

Each row defines one relance: which template to use and how many days after the
*previous* send (J1 or prior follow-up) it should be dispatched.  The worker
creates EmailQueue rows from this list after each successful J1 send.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base

if TYPE_CHECKING:
    from models.campaign import Campaign
    from models.email_template import EmailTemplate


class CampaignFollowUp(Base):
    """
    A single follow-up step in a campaign sequence.

    Attributes:
        id:          Primary key.
        campaign_id: Parent campaign (cascade delete).
        template_id: Template to render for this follow-up.
        delay_days:  Days after the *previous* send before dispatching.
        position:    1-based ordering within the sequence.
        created_at:  Row creation timestamp.
    """

    __tablename__ = "campaign_follow_ups"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[int] = mapped_column(
        ForeignKey("email_templates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    delay_days: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    campaign: Mapped[Campaign] = relationship("Campaign", back_populates="follow_ups")
    template: Mapped[EmailTemplate] = relationship("EmailTemplate")

    def __repr__(self) -> str:
        return (
            f"<CampaignFollowUp id={self.id} campaign={self.campaign_id} pos={self.position} delay={self.delay_days}d>"
        )
