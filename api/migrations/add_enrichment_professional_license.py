"""Add the professional license (label, number, source) to enrichments.

Each column is checked against INFORMATION_SCHEMA before its ALTER: prod and local schemas diverge.
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

_COLUMNS: tuple[tuple[str, str], ...] = (
    ("professional_license_label", "VARCHAR(60) NULL"),
    ("professional_license_number", "VARCHAR(60) NULL"),
    ("professional_license_source", "VARCHAR(50) NULL"),
)


def _column_exists(conn: Connection, column_name: str) -> bool:
    result = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'prospect_enrichments'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        for column_name, definition in _COLUMNS:
            if not _column_exists(conn, column_name):
                conn.execute(text(f"ALTER TABLE prospect_enrichments ADD COLUMN {column_name} {definition}"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("prospect_enrichments.professional_license_* columns ensured.")
