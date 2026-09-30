"""
Scheduled email model — a message written now, sent later by the worker.

First use: answering a prospect's reply from the conversation drawer at a chosen
time (``kind = conversation_reply``). The row keeps everything the send needs, so
the worker replays the exact same path as an immediate answer.
"""

from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import UTF8MB4_TABLE_OPTIONS, Base


class ScheduledEmail(Base):
    """
    One email planned for an exact time.

    Attributes:
        id: Unique identifier
        user_id: Owner (the sender)
        kind: What the send is (``conversation_reply`` for now)
        reply_id: The prospect reply being answered (conversation replies)
        prospect_id: Prospect the email goes to, when known
        recipient_email: Address the email goes to
        body_html: The message as written, without signature (added at send time)
        scheduled_at: Planned send time (naive UTC)
        status: ``pending`` / ``sending`` / ``sent`` / ``failed`` / ``cancelled``
        email_log_id: The EmailLog created by the actual send
        error_message: Why the send failed
        sent_at: When it actually went out
        created_at: When it was planned
        updated_at: Last change
    """

    __tablename__ = "scheduled_emails"
    __table_args__ = (UTF8MB4_TABLE_OPTIONS,)

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="conversation_reply")
    reply_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    prospect_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    email_log_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.utcnow, nullable=True)
