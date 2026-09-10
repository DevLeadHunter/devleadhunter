"""Per-user SMS sending configuration.

The smsmode account is a single platform account; what varies per user is the
**alphanumeric sender** (≤11 chars, e.g. « Dibodev »), configured here the same
way the email sending identity is configured per user. No API key is stored: the
key is a platform-level secret injected server-side.
"""

from datetime import datetime

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class SmsConfig(Base):
    """A user's SMS sender identity + enable flag.

    Attributes:
        id: Unique identifier (auto-increment)
        user_id: Owner of the configuration (one row per user)
        sender: Alphanumeric sender id shown on the prospect's phone (≤11 chars)
        enabled: Whether the user opted the SMS channel on
        cold_sms_enabled: Auto cold-SMS prospects who have a mobile but no email
        auto_relance_enabled: Auto-relance by SMS the emailed prospects who never reacted
        auto_relance_after_days: Days after the unanswered email before the auto-relance fires
        relance_template_key: Key of the SMS library template a J+30 relance renders
        created_at: Creation timestamp
        updated_at: Last-update timestamp
    """

    __tablename__ = "sms_configs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    sender: Mapped[str] = mapped_column(String(11), nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    cold_sms_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    auto_relance_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    auto_relance_after_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30, server_default="30")
    relance_template_key: Mapped[str] = mapped_column(
        String(64), nullable=False, default="rappel-court", server_default="rappel-court"
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.utcnow, nullable=True)
