"""Add ``onboarding_completed`` to users (setup wizard state).

New accounts land on ``/configuration`` right after signup and only flip this
flag once they finish the wizard. Accounts that already exist when this
migration runs were configured by hand, so they are backfilled to ``TRUE`` —
nobody gets sent back through a setup they already did.
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
              AND TABLE_NAME = 'users'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "onboarding_completed"):
            conn.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN onboarding_completed TINYINT(1) NOT NULL DEFAULT 0
                    """
                )
            )
            # Existing accounts are already set up — do not nag them.
            conn.execute(text("UPDATE users SET onboarding_completed = 1"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("users.onboarding_completed ensured.")
