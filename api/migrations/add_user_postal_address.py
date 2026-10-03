"""Add ``postal_address`` to users (sender identification required by Canada's anti-spam law).

Printed in the footer of commercial emails to Canadian prospects (CASL); while it is empty, no such
email leaves. Nullable, no backfill: each user fills in his own. The column is checked against
INFORMATION_SCHEMA before its ALTER: prod and local schemas diverge.
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
    """Whether ``users`` already has the column (read on the live schema)."""
    result = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'users'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    """Add the missing column (re-runnable)."""
    with engine.connect() as connection:
        if not _column_exists(connection, "postal_address"):
            connection.execute(text("ALTER TABLE users ADD COLUMN postal_address VARCHAR(500) NULL"))
        connection.commit()


if __name__ == "__main__":
    run_migration()
    print("users.postal_address ensured.")
