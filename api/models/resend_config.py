"""
ResendConfig model — per-user Resend email provider settings.

The API key and webhook secret are stored encrypted (Fernet symmetric
encryption via EncryptionService) so they are never readable in plain text
from the database.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base


class ResendConfig(Base):
    """
    Per-user Resend configuration.

    Attributes:
        id:               Primary key.
        user_id:          Owner — one config row per user (UNIQUE constraint).
        api_key:          Encrypted Resend API key (``re_…``).
        webhook_secret:   Encrypted Resend webhook signing secret (``whsec_…``).
        from_email:       Sender address verified on Resend (e.g. ``leo@mail.dibodev.fr``).
        from_name:        Sender display name shown to recipients.
        created_at:       Row creation timestamp.
        updated_at:       Last modification timestamp (auto-updated by DB).
    """

    __tablename__ = "resend_config"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Stored encrypted — never plain text
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    webhook_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now(), nullable=True)

    user = relationship("User")

    def __repr__(self) -> str:
        return f"<ResendConfig user_id={self.user_id} from_email={self.from_email!r}>"
