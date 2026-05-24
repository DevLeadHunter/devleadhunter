"""Execute database migrations in order.

Each migration runs at most once: the module name is recorded in ``schema_migrations``.
Before applying tracked migrations, ``init_db()`` ensures all SQLAlchemy model tables exist.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import create_engine, text

from core.config import settings
from core.database import init_db

_SCHEMA_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  name VARCHAR(255) NOT NULL PRIMARY KEY,
  applied_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

# Order matters for incremental upgrades on existing databases.
MIGRATION_MODULES: list[tuple[str, str]] = [
    ("add_prospects_table", "migrations.add_prospects_table"),
    ("add_minimum_credits_purchase", "migrations.add_minimum_credits_purchase"),
    ("add_campaigns_table", "migrations.add_campaigns_table"),
    ("add_demo_sites_table", "migrations.add_demo_sites_table"),
    ("add_demo_site_verification_columns", "migrations.add_demo_site_verification_columns"),
    ("add_demo_site_storyblok_invite_sent", "migrations.add_demo_site_storyblok_invite_sent"),
]


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(_ROOT / ".env")


def _is_applied(engine, name: str) -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM schema_migrations WHERE name = :name"),
            {"name": name},
        ).first()
    return row is not None


def _mark_applied(engine, name: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO schema_migrations (name) VALUES (:name)"),
            {"name": name},
        )


def _run_module_migration(module_name: str) -> None:
    module = importlib.import_module(module_name)
    run_migration = getattr(module, "run_migration", None)
    if run_migration is None:
        raise RuntimeError(f"{module_name} must define run_migration()")
    run_migration()


def main() -> None:
    _load_dotenv()
    engine = create_engine(settings.database_url)

    with engine.begin() as conn:
        conn.execute(text(_SCHEMA_TABLE_DDL))

    print("Ensuring base schema from SQLAlchemy models...")
    init_db()
    print("Base schema ensured.")

    for migration_name, module_name in MIGRATION_MODULES:
        if _is_applied(engine, migration_name):
            print(f"Skipped (already applied): {migration_name}")
            continue

        print(f"Applying: {migration_name}")
        _run_module_migration(module_name)
        _mark_applied(engine, migration_name)
        print(f"Applied: {migration_name}")

    print("All migrations complete.")


if __name__ == "__main__":
    main()
