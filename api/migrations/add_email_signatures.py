"""Migration: create ``email_signatures`` + add ``email_templates.signature_id``.

Signatures are a new reusable sign-off block a user attaches to templates (and
picks in the manual composer). The FK column is added as a plain nullable INT on
existing databases — the delete route detaches referencing templates explicitly,
so no hard DB cascade is required here.

Run with:
    python migrations/add_email_signatures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine
from models.email_signature import EmailSignature


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(
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
    # 1. Create the email_signatures table (no-op if it already exists).
    EmailSignature.__table__.create(engine, checkfirst=True)

    # 2. Add the nullable signature_id column to email_templates.
    with engine.connect() as conn:
        if not _column_exists(conn, "email_templates", "signature_id"):
            conn.execute(text("ALTER TABLE email_templates ADD COLUMN signature_id INT NULL"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("email_signatures + email_templates.signature_id ensured.")
