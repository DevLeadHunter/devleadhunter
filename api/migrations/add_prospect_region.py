"""Add ``region`` to prospects: the French overseas department a prospect lives in (« MQ »), NULL elsewhere.

The model fills it on every write, from the address and the numbers; the prospects already stored are placed
here once, with the same rule. The column is checked against INFORMATION_SCHEMA before its ALTER: prod and
local schemas diverge.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import text
from sqlalchemy.engine import Connection

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine
from services.french_overseas import FrenchOverseas


def _column_exists(connection: Connection, table_name: str, column_name: str) -> bool:
    """Whether the table already has the column (read on the live schema)."""
    result = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table_name
              AND COLUMN_NAME = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return bool(result.scalar())


def _phones_of(raw_phones: object) -> list[str]:
    """The stored phone list, whether the driver hands the JSON column back parsed or as text."""
    if isinstance(raw_phones, str):
        try:
            raw_phones = json.loads(raw_phones)
        except ValueError:
            return []
    return [phone for phone in raw_phones or [] if isinstance(phone, str)] if isinstance(raw_phones, list) else []


def run_migration() -> None:
    """Add the missing column, then place the stored French prospects (re-runnable)."""
    with engine.connect() as connection:
        if not _column_exists(connection, "prospects", "region"):
            connection.execute(text("ALTER TABLE prospects ADD COLUMN region VARCHAR(2) NULL"))
            connection.execute(text("CREATE INDEX ix_prospects_region ON prospects (region)"))
        rows = connection.execute(
            text("SELECT id, country, address, phone, phones FROM prospects WHERE region IS NULL")
        ).all()
        for row in rows:
            prospect = SimpleNamespace(
                country=row.country, address=row.address, phone=row.phone, phones=_phones_of(row.phones)
            )
            department = FrenchOverseas.of_prospect(prospect)
            if department is not None:
                connection.execute(
                    text("UPDATE prospects SET region = :region WHERE id = :id"),
                    {"region": department.code, "id": row.id},
                )
        connection.commit()


if __name__ == "__main__":
    run_migration()
    print("prospects.region ensured.")
