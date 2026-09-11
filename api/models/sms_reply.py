"""Log of an inbound SMS reply, typed in by the operator.

The alphanumeric sender is one-way: a prospect's reply lands on the operator's
own phone, never in the app. This row is the manual record of that reply, so the
SMS thread of a prospect survives in the tool like email replies do.
"""

from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class SmsReply(Base):
    """An SMS received from a prospect, consigned by hand from the tracking page.

    Attributes:
        id: Unique identifier (auto-increment)
        user_id: Owner (the operator who received and consigned the reply)
        prospect_id: Prospect the reply belongs to (``None`` for a bare number)
        from_number: Normalised E.164 number the prospect wrote from
        body: Message text as received
        received_at: When the reply arrived (editable at consignment, UTC naive)
        created_at: When the row was consigned (UTC naive)
    """

    __tablename__ = "sms_replies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    prospect_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    from_number: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
