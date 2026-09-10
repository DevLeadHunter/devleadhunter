"""
Migration: shift ``sms_messages.created_at`` from MySQL server time to UTC.

``created_at`` was filled by ``server_default=func.now()`` — the MySQL server
clock, which is not UTC in prod — while ``delivered_at`` is written in UTC by
the API, so the drawer could show an SMS delivered two hours before it was
sent. The model now writes ``created_at`` in UTC too; this shifts the existing
rows by the server's UTC offset, measured at run time (prod and local do not
share a timezone, per the schema-divergence rule). Every existing row sits in
the same DST period (feature shipped 2026-09-03), so one uniform offset is
correct. No-op on a server already running on UTC.

Run with:
    python migrations/fix_sms_created_at_utc.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def run_migration() -> None:
    print("Running migration: fix_sms_created_at_utc")
    with engine.connect() as conn:
        offset_minutes = conn.execute(text("SELECT TIMESTAMPDIFF(MINUTE, UTC_TIMESTAMP(), NOW())")).scalar() or 0
        if offset_minutes == 0:
            print("  = MySQL clock already on UTC, nothing to shift")
            return
        result = conn.execute(
            text("UPDATE sms_messages SET created_at = DATE_SUB(created_at, INTERVAL :offset MINUTE)"),
            {"offset": offset_minutes},
        )
        conn.commit()
    print(f"  + shifted created_at by -{offset_minutes} min on {result.rowcount} SMS")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Shift sms_messages.created_at to UTC")
    print("=" * 60)
    run_migration()
