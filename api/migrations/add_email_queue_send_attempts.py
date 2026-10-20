"""Add ``send_attempts`` to the email queue: how many times a send was re-planned on a network cut.

When the server cannot reach Resend even after the sender's own retries, the queue item goes back
to ``pending`` a few minutes later instead of failing. This column bounds those re-plans. Re-runnable:
the column is checked against INFORMATION_SCHEMA first.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine


def _column_exists(connection: Connection, column_name: str) -> bool:
    """Whether ``email_queue`` already has the column (read on the live schema)."""
    result = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'email_queue'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    """Add the column when it is missing."""
    with engine.connect() as connection:
        if not _column_exists(connection, "send_attempts"):
            connection.execute(text("ALTER TABLE email_queue ADD COLUMN send_attempts INT NOT NULL DEFAULT 0"))
        connection.commit()


if __name__ == "__main__":
    run_migration()
    print("email_queue.send_attempts is in place.")
