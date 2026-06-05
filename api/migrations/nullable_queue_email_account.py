"""
Migration: make email_queue.email_account_id nullable.

Campaigns now send via the user's ResendConfig instead of a selected
EmailAccount, so queue items no longer require an email_account_id.

Run with:
    python migrations/nullable_queue_email_account.py
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from core.database import engine


def run_migration() -> None:
    print("Running migration: nullable_queue_email_account")
    with engine.connect() as conn:
        # Drop the existing FK (name is auto-generated; resolve it dynamically),
        # widen the column to NULL, then re-add the FK with ON DELETE SET NULL.
        fk_row = conn.execute(text(
            "SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE "
            "WHERE TABLE_NAME = 'email_queue' "
            "AND COLUMN_NAME = 'email_account_id' "
            "AND REFERENCED_TABLE_NAME = 'email_accounts' "
            "AND TABLE_SCHEMA = DATABASE() LIMIT 1"
        )).first()

        if fk_row:
            conn.execute(text(f"ALTER TABLE email_queue DROP FOREIGN KEY {fk_row[0]}"))

        conn.execute(text(
            "ALTER TABLE email_queue MODIFY COLUMN email_account_id INT NULL"
        ))
        conn.execute(text(
            "ALTER TABLE email_queue "
            "ADD CONSTRAINT fk_email_queue_account "
            "FOREIGN KEY (email_account_id) REFERENCES email_accounts(id) ON DELETE SET NULL"
        ))
        conn.commit()
    print("  ~ email_queue.email_account_id: NULL now allowed")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Nullable email_queue.email_account_id")
    print("=" * 60)
    run_migration()
