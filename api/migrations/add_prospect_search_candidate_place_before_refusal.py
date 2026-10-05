"""Add ``status_before_refusal`` and ``detail_before_refusal`` to prospect_search_candidates.

When the user refuses a lead, its place (complete, a single contact, to check) and the detail that
explains it are kept aside, so that undoing the refusal gives the lead back exactly as it was: a lead
the search could not verify must not come back as complete. Both columns stay empty for the leads
refused before they existed; undoing such a refusal decides the place again, as before.

The columns are checked against INFORMATION_SCHEMA before their ALTER: prod and local schemas diverge.
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

_TABLE_NAME: str = "prospect_search_candidates"

_COLUMNS: tuple[tuple[str, str], ...] = (
    ("status_before_refusal", "VARCHAR(20) NULL"),
    ("detail_before_refusal", "VARCHAR(500) NULL"),
)


def _column_exists(connection: Connection, table_name: str, column_name: str) -> bool:
    """Whether the table already has the column (read on the live schema)."""
    result = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table_name
              AND COLUMN_NAME = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    """Add the missing columns (re-runnable: an existing column is left as is)."""
    with engine.connect() as connection:
        for column_name, column_type in _COLUMNS:
            if _column_exists(connection, _TABLE_NAME, column_name):
                continue
            connection.execute(text(f"ALTER TABLE {_TABLE_NAME} ADD COLUMN {column_name} {column_type}"))
        connection.commit()


if __name__ == "__main__":
    run_migration()
    print("prospect_search_candidates.status_before_refusal and detail_before_refusal ensured.")
