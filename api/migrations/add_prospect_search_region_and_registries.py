"""Add ``region`` and ``use_registries`` to prospect_searches.

``region`` names the French overseas department a search walks instead of mainland France
(« MQ » for Martinique); the searches already stored searched their country, they keep ``NULL``.
``use_registries`` tells whether the public registries with emails (RGE, RBQ) are read before Google
and Facebook: every search so far read them, so the column comes with ``1``, its SQL default, which
also keeps that behaviour for a search the former process creates during a deployment. Each column
is checked against INFORMATION_SCHEMA before its ALTER: prod and local schemas diverge.
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

_COLUMN_DEFINITIONS: dict[str, str] = {
    "region": "VARCHAR(2) NULL",
    "use_registries": "BOOLEAN NOT NULL DEFAULT 1",
}


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
        for column_name, definition in _COLUMN_DEFINITIONS.items():
            if not _column_exists(connection, "prospect_searches", column_name):
                connection.execute(text(f"ALTER TABLE prospect_searches ADD COLUMN {column_name} {definition}"))
        connection.commit()


if __name__ == "__main__":
    run_migration()
    print("prospect_searches.region and prospect_searches.use_registries ensured.")
