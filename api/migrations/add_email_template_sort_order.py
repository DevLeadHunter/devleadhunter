"""Add sort_order to email_templates (pin recommended templates first).

Also applies a one-time content fix: an already-seeded variant B ended with an
English CTA (``Worth a look ?``). The seeder is insert-only (skips existing rows
by name), so this migration corrects the row that is already in the database.
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
              AND TABLE_NAME = 'email_templates'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "sort_order"):
            conn.execute(
                text(
                    """
                    ALTER TABLE email_templates
                    ADD COLUMN sort_order INT NOT NULL DEFAULT 0,
                    ADD INDEX ix_email_templates_sort_order (sort_order)
                    """
                )
            )
        # One-time fix of the already-seeded variant B (English CTA → French).
        # Idempotent: REPLACE is a no-op once the row no longer contains the string.
        conn.execute(
            text("UPDATE email_templates SET body_html = REPLACE(body_html, :old, :new)"),
            {"old": "<p>Worth a look ?</p>", "new": "<p>Ça vaut le coup d'œil ?</p>"},
        )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("email_templates.sort_order ensured + variant B CTA fixed.")
