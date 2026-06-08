"""Add prospect_id column to demo_sites (link a demo site to its source prospect)."""

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
              AND TABLE_NAME = 'demo_sites'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "prospect_id"):
            conn.execute(
                text(
                    """
                    ALTER TABLE demo_sites
                    ADD COLUMN prospect_id INT NULL,
                    ADD INDEX ix_demo_sites_prospect_id (prospect_id)
                    """
                )
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("demo_sites.prospect_id column ensured.")
