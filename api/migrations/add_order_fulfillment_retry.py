"""Add fulfilment-retry tracking columns to orders (attempts + last error)."""

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
              AND TABLE_NAME = 'orders'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    """Add ``fulfillment_attempts`` and ``fulfillment_last_error`` if missing (idempotent)."""
    with engine.connect() as conn:
        if not _column_exists(conn, "fulfillment_attempts"):
            conn.execute(
                text(
                    "ALTER TABLE orders "
                    "ADD COLUMN fulfillment_attempts INT NOT NULL DEFAULT 0"
                )
            )
        if not _column_exists(conn, "fulfillment_last_error"):
            conn.execute(
                text(
                    "ALTER TABLE orders "
                    "ADD COLUMN fulfillment_last_error VARCHAR(500) NULL"
                )
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("orders fulfilment-retry columns ensured.")
