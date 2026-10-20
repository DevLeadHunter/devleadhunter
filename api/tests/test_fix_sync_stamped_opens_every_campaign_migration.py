"""
Tests for the campaign-wide repair of the opens stamped by the Resend sync on 2026-10-20.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from migrations.fix_sync_stamped_opens_every_campaign import SYNC_STAMP, run_migration
from models.email_log import EmailLog

_HUMAN_OPEN_AT_THE_SAME_SECOND = SYNC_STAMP


def _email_log(email_log_id: int, status: str, opened_at: datetime | None, open_count: int) -> EmailLog:
    """An email log of any campaign with the given open state."""
    return EmailLog(
        id=email_log_id,
        user_id=1,
        campaign_id=str(email_log_id % 3),
        recipient_email=f"prospect-{email_log_id}@example.com",
        subject="le site",
        body_html="<p>le site</p>",
        provider="resend",
        status=status,
        sent_at=datetime(2026, 10, 20, 9, 30),
        delivered_at=datetime(2026, 10, 20, 9, 30, 3),
        opened_at=opened_at,
        open_count=open_count,
    )


def test_every_stamped_open_without_a_counted_human_open_is_reset(engine: Engine, db: Session) -> None:
    """Rows of any campaign carrying the stamp with no human open counted go back to delivered."""
    db.add_all(
        [
            _email_log(240, "opened", SYNC_STAMP, open_count=0),
            _email_log(259, "clicked", SYNC_STAMP, open_count=0),
            _email_log(300, "opened", _HUMAN_OPEN_AT_THE_SAME_SECOND, open_count=1),
            _email_log(301, "opened", datetime(2026, 10, 20, 15, 2, 11), open_count=1),
        ]
    )
    db.commit()

    run_migration(engine)
    db.expire_all()

    rows = {row.id: row for row in db.execute(select(EmailLog)).scalars()}
    assert rows[240].opened_at is None
    assert rows[240].status == "delivered"
    assert rows[259].opened_at is None
    assert rows[259].status == "clicked"
    assert rows[300].opened_at == SYNC_STAMP
    assert rows[300].status == "opened"
    assert rows[301].status == "opened"
