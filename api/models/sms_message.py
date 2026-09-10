"""Log of an outbound SMS (one row per send)."""

from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class SmsMessage(Base):
    """A relance SMS sent (or attempted) to a prospect.

    Attributes:
        id: Unique identifier (auto-increment)
        user_id: Sender (owner of the prospect)
        prospect_id: Recipient prospect (``None`` for a manual send to a bare number)
        recipient_name: Display label for a manual send (no saved prospect)
        to_e164: Normalised recipient number
        sender: Alphanumeric sender used
        body: Message body sent
        status: Lifecycle status (:class:`~enums.sms_status.SmsStatus` value)
        status_detail: Human delivery reason from the DLR (e.g. ``Spam``), when known
        provider_message_id: Provider id, to match DLR callbacks
        price_cents: Cost of the send in cents, when known
        segments: Number of billed SMS segments
        error: Failure reason when status is ``failed``
        created_at: When the send was recorded
        delivered_at: When the DLR confirmed delivery
    """

    __tablename__ = "sms_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    prospect_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    recipient_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    to_e164: Mapped[str] = mapped_column(String(20), nullable=False)
    sender: Mapped[str] = mapped_column(String(11), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    status_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    segments: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # UTC (Python-side), like delivered_at — the MySQL clock is not UTC in prod.
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False, index=True)
    delivered_at: Mapped[datetime | None] = mapped_column(nullable=True)
