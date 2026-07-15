"""Add Lighthouse audit columns (existing-website quality) to prospects."""

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
        if not _column_exists(conn, "lighthouse_json"):
            conn.execute(
                text(
                    """
                    ALTER TABLE prospects
                    ADD COLUMN lighthouse_json JSON NULL,
                    ADD COLUMN lighthouse_at DATETIME NULL
                    """
                )
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("prospects.lighthouse columns ensured.")
