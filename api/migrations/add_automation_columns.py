"""
Migration — automatisation tunnel columns + send_policies table.

Idempotent:
  * new ``send_policies`` table via ``checkfirst``;
  * per-prospect template + vendability columns on ``acquisition_run_items``;
  * full-auto target columns on ``acquisition_runs``.
Each ALTER is guarded with an INFORMATION_SCHEMA check so re-running is a no-op.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402

from core.database import engine  # noqa: E402
from models.send_policy import SendPolicy  # noqa: E402

# (table, column, DDL type) for each column to add if missing.
_COLUMNS: list[tuple[str, str, str]] = [
    ("acquisition_run_items", "template_id", "VARCHAR(64) NULL"),
    ("acquisition_run_items", "quality_score", "INT NULL"),
    ("acquisition_run_items", "quality_flags", "JSON NULL"),
    ("acquisition_runs", "search_metiers", "JSON NULL"),
    ("acquisition_runs", "search_villes", "JSON NULL"),
    ("acquisition_runs", "target_days", "INT NULL"),
]


def _column_exists(conn, table: str, column: str) -> bool:
    """Return True when ``table.column`` already exists in the current schema."""
    result = conn.execute(
        text(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
        ),
        {"t": table, "c": column},
    ).scalar()
    return bool(result)


def _table_exists(conn, table: str) -> bool:
    """Return True when ``table`` exists in the current schema."""
    result = conn.execute(
        text(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
        ),
        {"t": table},
    ).scalar()
    return bool(result)


def run_migration() -> None:
    """Create send_policies and add the new automatisation columns (idempotent)."""
    SendPolicy.__table__.create(engine, checkfirst=True)

    with engine.begin() as conn:
        for table, column, ddl in _COLUMNS:
            # Skip cleanly if the parent table doesn't exist yet (fresh DBs get
            # the columns from create_all before migrations run).
            if not _table_exists(conn, table):
                continue
            if _column_exists(conn, table, column):
                continue
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


if __name__ == "__main__":
    run_migration()
    print("✓ automation columns ready")
