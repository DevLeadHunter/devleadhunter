"""
Migration: make email_logs.email_account_id nullable.

Needed so emails sent directly via resend_config (no EmailAccount row)
can still be logged without a FK violation.

Run with:
    python migrations/nullable_email_account_id.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def run_migration() -> None:
    print("Running migration: nullable_email_account_id")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE email_logs MODIFY COLUMN email_account_id INT NULL"))
        conn.commit()
    print("  ~ email_logs.email_account_id: NULL now allowed")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Nullable email_account_id")
    print("=" * 60)
    run_migration()
