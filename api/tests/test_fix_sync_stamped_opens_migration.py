"""
Tests for the data repair of the opens stamped by the Resend sync on 2026-10-20.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from migrations.fix_sync_stamped_opens import SYNC_STAMP, run_migration
from models.email_log import EmailLog

_LATER_HUMAN_OPEN = datetime(2026, 10, 20, 16, 2, 11)


def _stamped_email_log(email_log_id: int, status: str, last_open_at: datetime | None = None) -> EmailLog:
    """An email log whose opened_at carries the sync stamp."""
    return EmailLog(
        id=email_log_id,
        user_id=1,
        recipient_email=f"prospect-{email_log_id}@example.com",
        subject="le site",
        body_html="<p>le site</p>",
        provider="resend",
        status=status,
        sent_at=datetime(2026, 10, 20, 9, 30),
        delivered_at=datetime(2026, 10, 20, 9, 30, 3),
        opened_at=SYNC_STAMP,
        last_open_at=last_open_at,
    )


def test_stamped_opens_are_reset_and_a_real_later_open_is_kept(engine: Engine, db: Session) -> None:
    """Only the listed rows change: a bare stamp is cleared, a real later open replaces the stamp."""
    db.add_all(
        [
            _stamped_email_log(236, "opened"),
            _stamped_email_log(237, "clicked", last_open_at=_LATER_HUMAN_OPEN),
            _stamped_email_log(999, "opened"),
        ]
    )
    db.commit()

    run_migration(engine)
    db.expire_all()

    rows = {row.id: row for row in db.execute(select(EmailLog)).scalars()}
    assert rows[236].opened_at is None
    assert rows[236].status == "delivered"
    assert rows[237].opened_at == _LATER_HUMAN_OPEN
    assert rows[237].status == "clicked"
    assert rows[999].opened_at == SYNC_STAMP
    assert rows[999].status == "opened"


def test_the_repair_is_re_runnable(engine: Engine, db: Session) -> None:
    """A second pass finds nothing left to change."""
    db.add(_stamped_email_log(239, "opened"))
    db.commit()

    run_migration(engine)
    run_migration(engine)
    db.expire_all()

    row = db.get(EmailLog, 239)
    assert row is not None
    assert row.opened_at is None
    assert row.status == "delivered"
