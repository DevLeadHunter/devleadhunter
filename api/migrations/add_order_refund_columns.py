"""Add refund tracking columns to orders (stripe_payment_intent_id, refunded_at)."""

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
              AND TABLE_NAME = 'orders'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def _table_exists(conn) -> bool:
    result = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'orders'
            """
        )
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        # If the table does not exist yet, init_db() create_all will build it
        # with all columns — nothing to do here.
        if not _table_exists(conn):
            return
        if not _column_exists(conn, "stripe_payment_intent_id"):
            conn.execute(
                text(
                    """
                    ALTER TABLE orders
                    ADD COLUMN stripe_payment_intent_id VARCHAR(255) NULL,
                    ADD INDEX ix_orders_stripe_payment_intent_id (stripe_payment_intent_id)
                    """
                )
            )
        if not _column_exists(conn, "refunded_at"):
            conn.execute(text("ALTER TABLE orders ADD COLUMN refunded_at DATETIME NULL"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("orders refund columns ensured.")
