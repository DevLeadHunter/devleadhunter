"""Add revived_at to sms_auto_queue (a relance J+30 revived by hand despite an earlier email reply)."""

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
              AND TABLE_NAME = 'sms_auto_queue'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "revived_at"):
            conn.execute(text("ALTER TABLE sms_auto_queue ADD COLUMN revived_at DATETIME NULL AFTER skip_reason"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("sms_auto_queue.revived_at column ensured.")
