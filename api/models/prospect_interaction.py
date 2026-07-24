"""
Prospect interaction model for tracking interactions history.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.database import Base


class ProspectInteraction(Base):
    """
    Prospect interaction model for tracking all interactions with prospects.

    Attributes:
        id: Unique identifier
        prospect_id: ID of the prospect
        user_id: ID of the user who made the interaction
        interaction_type: Type of interaction (email_sent, email_opened, email_clicked, call, meeting, note, etc.)
        description: Description of the interaction
        interaction_metadata: JSON metadata for additional information
        created_at: Timestamp when interaction was created
    """

    __tablename__ = "prospect_interactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    interaction_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    interaction_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False, index=True)

    def __repr__(self) -> str:
        """String representation of the interaction."""
        return f"<ProspectInteraction id={self.id} prospect_id={self.prospect_id} type={self.interaction_type}>"
