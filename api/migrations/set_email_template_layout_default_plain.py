"""Make ``plain`` the database default of ``email_templates.layout`` again.

The wave 4 A/B test sent the same text in both dressings: the card with the offer table made 1 prospect
in 35 click, the plain email 7 in 33. Every template went back to plain on 2026-10-22, and a new template
is born plain again. Existing rows are not touched. The column is checked against INFORMATION_SCHEMA
first: prod and local schemas diverge.
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
    """Set the column default (re-runnable)."""
    with engine.connect() as connection:
        if _column_exists(connection, "email_templates", "layout"):
            connection.execute(text("ALTER TABLE email_templates ALTER COLUMN layout SET DEFAULT 'plain'"))
        connection.commit()


if __name__ == "__main__":
    run_migration()
    print("email_templates.layout now defaults to plain.")
