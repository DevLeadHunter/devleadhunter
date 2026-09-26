"""Add status + updated_at to demo_site_leads.

``status`` tells a real ``submitted`` lead apart from a ``draft`` — a message the
prospect typed then left without sending, now captured so their words are never lost.
Existing rows are real submissions, so they default to ``submitted``.
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
              AND TABLE_NAME = 'demo_site_leads'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "status"):
            conn.execute(
                text(
                    """
                    ALTER TABLE demo_site_leads
                    ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'submitted',
                    ADD INDEX ix_demo_site_leads_status (status)
                    """
                )
            )
        if not _column_exists(conn, "updated_at"):
            conn.execute(text("ALTER TABLE demo_site_leads ADD COLUMN updated_at DATETIME(6) NULL"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("demo_site_leads.status + updated_at columns ensured.")
