"""SMS opt-out list (STOP) — never text these numbers again."""

from datetime import datetime

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class SmsSuppression(Base):
    """A number that replied STOP (or was manually opted out) for a user.

    Scoped per user: a prospect opting out of one sender does not opt out of
    another user's sends. Checked before every send, hard block.

    Attributes:
        id: Unique identifier (auto-increment)
        user_id: Owner whose sends must skip this number
        phone_e164: Normalised opted-out number
        reason: Why it was suppressed (``stop`` | ``manual``)
        created_at: When it was recorded
    """

    __tablename__ = "sms_suppressions"
    __table_args__ = (UniqueConstraint("user_id", "phone_e164", name="uq_sms_suppression_user_phone"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    phone_e164: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(String(16), nullable=False, default="stop")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
