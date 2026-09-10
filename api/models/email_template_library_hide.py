"""
Per-user hide state for shared library email templates.

When a user « deletes » a library template, we record a hide row instead of
touching the canonical library row.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class EmailTemplateLibraryHide(Base):
    """Marks a library template as hidden for one user."""

    __tablename__ = "email_template_library_hides"
    __table_args__ = (UniqueConstraint("user_id", "library_template_id", name="uq_template_hide_user_library"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    library_template_id: Mapped[int] = mapped_column(
        ForeignKey("email_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
