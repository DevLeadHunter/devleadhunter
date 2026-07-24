"""
Email signature model.

A reusable sign-off block a user can attach to email templates (and pick in the
manual composer). Stored as HTML so a signature pasted from Gmail keeps its
formatting, links and logo. One signature per user may be the default.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base

if TYPE_CHECKING:
    from models.user import User


class EmailSignature(Base):
    """
    Reusable email signature owned by a user.

    Attributes:
        id: Unique identifier.
        user_id: Owner of the signature.
        name: Human label shown in the picker (e.g. "Signature Dibodev").
        content_html: Signature body in HTML (paste-friendly from Gmail).
        is_default: Whether this is the user's default signature.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "email_signatures"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_html: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now(), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="email_signatures")

    def __repr__(self) -> str:
        """String representation of the email signature."""
        return f"<EmailSignature id={self.id} name={self.name}>"
