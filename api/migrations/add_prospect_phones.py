"""Add ``phones`` to prospects (multi-number with primary, mirroring ``emails``).

JSON list of known numbers, best-first; ``phone`` stays synced to ``phones[0]``.
Nullable, no backfill: like ``emails``, the code falls back to the single legacy
column while the list is empty.
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
        if not _column_exists(conn, "phones"):
            conn.execute(text("ALTER TABLE prospects ADD COLUMN phones JSON NULL"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("prospects.phones ensured.")
