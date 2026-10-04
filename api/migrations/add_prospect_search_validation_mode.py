"""Add ``validation_mode`` to prospect_searches (who turns the candidates of a search into prospects).

A search either waits for the user to accept each candidate (``manual``, what a new search does
unless told otherwise) or creates the prospects itself (``automatic``, the behaviour so far). The
searches already stored ran with that former behaviour: they take ``automatic`` as the column is
added.

The column's SQL default stays ``automatic``: during a deployment the former process, still
serving, creates searches without knowing the column, and they must keep the former behaviour.
The application always writes the value itself (the model's default, ``manual``, is applied on the
Python side). The column is checked against INFORMATION_SCHEMA before its ALTER: prod and local
schemas diverge.
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
    """Add the missing column, the stored searches marked automatic (re-runnable: an existing column is left as is)."""
    with engine.connect() as connection:
        if _column_exists(connection, "prospect_searches", "validation_mode"):
            return
        connection.execute(
            text("ALTER TABLE prospect_searches ADD COLUMN validation_mode VARCHAR(16) NOT NULL DEFAULT 'automatic'")
        )
        connection.commit()


if __name__ == "__main__":
    run_migration()
    print("prospect_searches.validation_mode ensured.")
