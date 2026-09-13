"""
Migration: rename ``prospects.sms_relance_excluded`` to ``prospects.sms_auto_excluded``.

The flag now opts a prospect out of EVERY automated SMS (relance J+30 and cold first
contact), not only the relance — the column name follows. Guarded through
INFORMATION_SCHEMA so it works whether the old column exists (prod) or not (fresh DB).

Run with:
    python migrations/rename_prospect_sms_auto_excluded.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine

_COLUMN_EXISTS = (
    "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prospects' AND COLUMN_NAME = :column"
)


def run_migration() -> None:
    print("Running migration: rename_prospect_sms_auto_excluded")
    with engine.connect() as conn:
        has_old = bool(conn.execute(text(_COLUMN_EXISTS), {"column": "sms_relance_excluded"}).scalar())
        has_new = bool(conn.execute(text(_COLUMN_EXISTS), {"column": "sms_auto_excluded"}).scalar())
        if has_old and not has_new:
            conn.execute(
                text(
                    "ALTER TABLE prospects CHANGE sms_relance_excluded sms_auto_excluded TINYINT(1) NOT NULL DEFAULT 0"
                )
            )
            print("  ~ prospects.sms_relance_excluded -> sms_auto_excluded")
        elif not has_new:
            conn.execute(text("ALTER TABLE prospects ADD COLUMN sms_auto_excluded TINYINT(1) NOT NULL DEFAULT 0"))
            print("  + prospects.sms_auto_excluded")
        else:
            print("  = prospects.sms_auto_excluded already in place")
        conn.commit()
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Rename prospects sms_relance_excluded to sms_auto_excluded")
    print("=" * 60)
    run_migration()
