"""Add ``email_undeliverable`` columns to prospects (dead email address).

When a campaign email hard-bounces and no other address can be tried, the
prospect's email is a dead end. We flag it (instead of silently keeping the
prospect « contacté ») so the operator sees it and can recover the prospect
into an SMS campaign. Cleared automatically on the next successful delivery
or when the email is edited by hand.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine


def _column_exists(conn, column_name: str) -> bool:
    result = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'prospects'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "email_undeliverable"):
            conn.execute(
                text(
                    """
                    ALTER TABLE prospects
                    ADD COLUMN email_undeliverable TINYINT(1) NOT NULL DEFAULT 0
                    """
                )
            )
            conn.execute(text("CREATE INDEX ix_prospects_email_undeliverable ON prospects (email_undeliverable)"))
        if not _column_exists(conn, "email_undeliverable_at"):
            conn.execute(text("ALTER TABLE prospects ADD COLUMN email_undeliverable_at DATETIME NULL"))
        if not _column_exists(conn, "email_undeliverable_reason"):
            conn.execute(text("ALTER TABLE prospects ADD COLUMN email_undeliverable_reason VARCHAR(500) NULL"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("prospects.email_undeliverable columns ensured.")
