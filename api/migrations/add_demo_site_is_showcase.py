"""Add is_showcase to demo_sites (permanent showroom demos embedded by dibodev.fr)."""

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
        if not _column_exists(conn, "is_showcase"):
            conn.execute(
                text(
                    """
                    ALTER TABLE demo_sites
                    ADD COLUMN is_showcase TINYINT(1) NOT NULL DEFAULT 0
                    """
                )
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("demo_sites.is_showcase column ensured.")
