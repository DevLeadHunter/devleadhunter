"""Add ``sending_provider`` to users (active email-sending transport).

Each user sends outreach through exactly one provider (``resend`` | ``gmail``),
resolved by ``services.sending_identity``. Existing users default to ``resend``,
which preserves the previous behaviour (everyone sent via ResendConfig).
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
        if not _column_exists(conn, "sending_provider"):
            conn.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN sending_provider VARCHAR(20) NOT NULL DEFAULT 'resend'
                    """
                )
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("users.sending_provider ensured.")
