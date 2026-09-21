"""Add ``country`` to prospects (ISO 3166-1 alpha-2, default FR).

Existing rows are backfilled from their international phone prefix: the only
non-French prospects created before this column were Swiss (+41) and Belgian
(+32) ones, imported for the Europe test wave.
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
        if not _column_exists(conn, "country"):
            conn.execute(text("ALTER TABLE prospects ADD COLUMN country VARCHAR(2) NOT NULL DEFAULT 'FR'"))
            conn.execute(text("CREATE INDEX ix_prospects_country ON prospects (country)"))
        conn.execute(text("UPDATE prospects SET country = 'CH' WHERE phone LIKE '+41%' AND country = 'FR'"))
        conn.execute(text("UPDATE prospects SET country = 'BE' WHERE phone LIKE '+32%' AND country = 'FR'"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("prospects.country column ensured and backfilled from phone prefixes.")
