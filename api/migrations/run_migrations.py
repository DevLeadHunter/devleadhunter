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
    ("add_demo_site_storyblok_space_id_bigint", "migrations.add_demo_site_storyblok_space_id_bigint"),
    ("add_complained_at", "migrations.add_complained_at"),
    ("add_suppressed_at", "migrations.add_suppressed_at"),
    ("add_campaign_settings", "migrations.add_campaign_settings"),
    ("add_campaign_follow_ups_table", "migrations.add_campaign_follow_ups_table"),
    ("nullable_queue_email_account", "migrations.nullable_queue_email_account"),
    ("add_demo_site_prospect_id", "migrations.add_demo_site_prospect_id"),
    ("add_order_refund_columns", "migrations.add_order_refund_columns"),
    ("add_campaign_behavior_followups", "migrations.add_campaign_behavior_followups"),
    ("add_demo_site_custom_domain", "migrations.add_demo_site_custom_domain"),
    ("add_prospect_contacted", "migrations.add_prospect_contacted"),
    ("add_organizations", "migrations.add_organizations"),
    ("add_prospect_lighthouse", "migrations.add_prospect_lighthouse"),
    ("add_order_fulfillment_retry", "migrations.add_order_fulfillment_retry"),
    ("add_scraper_diagnostics", "migrations.add_scraper_diagnostics"),
    ("add_acquisition_tables", "migrations.add_acquisition_tables"),
    ("add_automation_columns", "migrations.add_automation_columns"),
    ("add_email_template_sort_order", "migrations.add_email_template_sort_order"),
    ("add_enrichment_contact_fields", "migrations.add_enrichment_contact_fields"),
    ("update_templates_salutation", "migrations.update_templates_salutation"),
    ("add_demo_video", "migrations.add_demo_video"),
    ("add_presenter_auto_generate", "migrations.add_presenter_auto_generate"),
    ("add_user_sending_provider", "migrations.add_user_sending_provider"),
    ("add_user_onboarding_completed", "migrations.add_user_onboarding_completed"),
    ("add_presenter_video_source", "migrations.add_presenter_video_source"),
    ("add_email_signatures", "migrations.add_email_signatures"),
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
