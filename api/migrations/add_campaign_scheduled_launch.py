"""Add the scheduled launch of a campaign: its time, the loop's claim and the reason of a missed launch.

Re-runnable.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine

_COLUMNS: tuple[tuple[str, str], ...] = (
    ("scheduled_launch_at", "DATETIME NULL"),
    ("scheduled_launch_claimed_at", "DATETIME NULL"),
    ("scheduled_launch_error", "VARCHAR(500) NULL"),
)


def run_migration(target_engine: Engine = engine) -> None:
    """Add each column the campaigns table does not have yet."""
    existing_columns: set[str] = {column["name"] for column in inspect(target_engine).get_columns("campaigns")}
    with target_engine.connect() as conn:
        for column_name, column_type in _COLUMNS:
            if column_name not in existing_columns:
                conn.execute(text(f"ALTER TABLE campaigns ADD COLUMN {column_name} {column_type}"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("campaigns.scheduled_launch_* columns ensured.")
