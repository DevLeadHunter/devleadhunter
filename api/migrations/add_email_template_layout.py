"""Add ``layout`` to email_templates and ``email_accent_color`` to users (the dressing of prospecting emails).

A template chooses how its email leaves: as plain paragraphs (``plain``, the behaviour so far, kept
for every existing row), in a card (``card``), or in a card whose offer is laid out as a table
(``card_table``). The colour of the links and of the button belongs to the sender: nullable, the
layout falls back to ink when a profile has none. Each column is checked against
INFORMATION_SCHEMA before its ALTER: prod and local schemas diverge.
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
    """Add the missing columns (re-runnable)."""
    with engine.connect() as connection:
        if not _column_exists(connection, "email_templates", "layout"):
            connection.execute(
                text("ALTER TABLE email_templates ADD COLUMN layout VARCHAR(20) NOT NULL DEFAULT 'plain'")
            )
        if not _column_exists(connection, "users", "email_accent_color"):
            connection.execute(text("ALTER TABLE users ADD COLUMN email_accent_color VARCHAR(7) NULL"))
        connection.commit()


if __name__ == "__main__":
    run_migration()
    print("email_templates.layout and users.email_accent_color ensured.")
