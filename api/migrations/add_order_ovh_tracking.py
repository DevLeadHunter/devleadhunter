"""Add OVH registrar tracking to orders (``ovh_order_id`` + ``ovh_order_status``).

The go-live action buys the domain through OVH but only returned the order id to the
caller: the operator had to open the OVH manager to know whether the payment was
validated or the domain delivered. Persisting the order id and its last-seen status
lets the fulfilment loop poll OVH and surface the real step in the sale drawer,
the activity log and push notifications.
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
              AND TABLE_NAME = 'orders'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "ovh_order_id"):
            conn.execute(text("ALTER TABLE orders ADD COLUMN ovh_order_id BIGINT NULL"))
        if not _column_exists(conn, "ovh_order_status"):
            conn.execute(text("ALTER TABLE orders ADD COLUMN ovh_order_status VARCHAR(32) NULL"))
        # One-off backfill: the only go-live bought before this feature (Mayer, 14/09/2026)
        # gets its known OVH order id, so the in-flight registration is followed immediately.
        conn.execute(
            text(
                """
                UPDATE orders SET ovh_order_id = 258872913
                WHERE domain = 'mayer-paysagiste-angers.fr' AND ovh_order_id IS NULL
                """
            )
        )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("orders.ovh_order_id and orders.ovh_order_status columns ensured.")
