"""Add ``contact_phone`` / ``contact_email`` to users (demo banner contact chips).

Optional public contacts shown as direct chips on the « Ce site vous plaît ? »
banner of demo and video pages. The display email is distinct from the login
email. Nullable, no backfill needed.
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
        if not _column_exists(conn, "contact_phone"):
            conn.execute(text("ALTER TABLE users ADD COLUMN contact_phone VARCHAR(30) NULL"))
        if not _column_exists(conn, "contact_email"):
            conn.execute(text("ALTER TABLE users ADD COLUMN contact_email VARCHAR(255) NULL"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("users.contact_phone / users.contact_email ensured.")
