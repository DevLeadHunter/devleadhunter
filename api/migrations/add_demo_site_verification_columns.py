"""Add verification columns to demo_sites."""

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
    """Add demo URL verification columns."""
    with engine.connect() as conn:
        if not _column_exists(conn, "demo_url_live"):
            conn.execute(
                text(
                    """
                    ALTER TABLE demo_sites
                    ADD COLUMN demo_url_live TINYINT(1) NOT NULL DEFAULT 0
                    """
                )
            )
        if not _column_exists(conn, "local_demo_url"):
            conn.execute(
                text(
                    """
                    ALTER TABLE demo_sites
                    ADD COLUMN local_demo_url VARCHAR(512) NULL
                    """
                )
            )
        if not _column_exists(conn, "verification_message"):
            conn.execute(
                text(
                    """
                    ALTER TABLE demo_sites
                    ADD COLUMN verification_message TEXT NULL
                    """
                )
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("demo_sites verification columns ensured.")
