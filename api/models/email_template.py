"""
Email template model for storing email templates.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from enums.email_template_category import EmailTemplateCategory

if TYPE_CHECKING:
    from models.email_account import EmailAccount
    from models.email_signature import EmailSignature
    from models.user import User


class EmailTemplate(Base):
    """
    Email template model for storing reusable email templates.

    Attributes:
        id: Unique identifier
        user_id: Foreign key to user
        email_account_id: Foreign key to email account (optional, can be selected at send time)
        name: Template name
        subject: Email subject (can include variables like {company_name})
        body_html: Email body in HTML format
        body_text: Email body in plain text format (optional)
        variables: JSON string of available variables (e.g., ["company_name", "contact_name"])
        is_active: Whether the template is active
        created_at: Timestamp when template was created
        updated_at: Timestamp when template was last updated
    """

    __tablename__ = "email_templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    email_account_id: Mapped[int | None] = mapped_column(ForeignKey("email_accounts.id"), nullable=True)
    # Optional signature appended to the rendered body at send time (opt-in switch).
    signature_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_signatures.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    variables: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Which step of the sequence this template is written for — drives the tabs of
    # the templates page. "first_email" (the J1 cold email) or "follow_up".
    category: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=EmailTemplateCategory.FIRST_EMAIL.value,
        default=EmailTemplateCategory.FIRST_EMAIL.value,
    )
    # Higher = pinned higher in the app's template list (recommended templates use a high value).
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", default=0)
    # Shared library templates (site-web module) are visible to every user but owned by the platform.
    is_library: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="0")
    # When set, this row is a per-user fork/customisation of the library template with this id.
    library_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.utcnow, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="email_templates")
    email_account: Mapped[Optional["EmailAccount"]] = relationship("EmailAccount", back_populates="email_templates")
    signature: Mapped[Optional["EmailSignature"]] = relationship("EmailSignature")

    def __repr__(self) -> str:
        """String representation of the email template."""
        return f"<EmailTemplate id={self.id} name={self.name}>"
