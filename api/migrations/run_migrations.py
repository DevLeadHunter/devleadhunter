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
    ("add_campaign_queue", "migrations.add_campaign_queue"),
    ("add_resend_config", "migrations.add_resend_config"),
    ("add_demo_sites_table", "migrations.add_demo_sites_table"),
    ("add_demo_site_verification_columns", "migrations.add_demo_site_verification_columns"),
    ("add_demo_site_storyblok_invite_sent", "migrations.add_demo_site_storyblok_invite_sent"),
    ("add_demo_site_storyblok_space_id_bigint", "migrations.add_demo_site_storyblok_space_id_bigint"),
    ("add_complained_at", "migrations.add_complained_at"),
    ("add_suppressed_at", "migrations.add_suppressed_at"),
    ("add_campaign_settings", "migrations.add_campaign_settings"),
    ("add_campaign_follow_ups_table", "migrations.add_campaign_follow_ups_table"),
    ("nullable_queue_email_account", "migrations.nullable_queue_email_account"),
    ("nullable_email_account_id", "migrations.nullable_email_account_id"),
    ("add_demo_site_prospect_id", "migrations.add_demo_site_prospect_id"),
    ("add_order_refund_columns", "migrations.add_order_refund_columns"),
    ("add_campaign_behavior_followups", "migrations.add_campaign_behavior_followups"),
    ("add_campaign_include_video", "migrations.add_campaign_include_video"),
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
    ("add_user_site_sale_price", "migrations.add_user_site_sale_price"),
    ("add_presenter_video_source", "migrations.add_presenter_video_source"),
    ("add_email_signatures", "migrations.add_email_signatures"),
    ("add_order_payment_provider_columns", "migrations.add_order_payment_provider_columns"),
    ("add_order_billing_details", "migrations.add_order_billing_details"),
    ("add_platform_commission_percent", "migrations.add_platform_commission_percent"),
    ("add_email_template_category", "migrations.add_email_template_category"),
    ("purge_demo_users", "migrations.purge_demo_users"),
    ("add_queue_skip_reason_and_follow_up_delay", "migrations.add_queue_skip_reason_and_follow_up_delay"),
    ("add_prospect_website_status", "migrations.add_prospect_website_status"),
    ("add_contact_proposal_tier", "migrations.add_contact_proposal_tier"),
    ("add_prospect_google_maps_url", "migrations.add_prospect_google_maps_url"),
    ("add_identity_check_fields", "migrations.add_identity_check_fields"),
    ("add_prospect_facebook_url", "migrations.add_prospect_facebook_url"),
    ("add_prospect_emails", "migrations.add_prospect_emails"),
    ("add_order_payment_link_id", "migrations.add_order_payment_link_id"),
    ("purge_orphan_deleted_demo_sites", "migrations.purge_orphan_deleted_demo_sites"),
    ("demote_social_websites", "migrations.demote_social_websites"),
    ("demote_platform_websites", "migrations.demote_platform_websites"),
    ("add_demo_site_use_brand_color", "migrations.add_demo_site_use_brand_color"),
    ("add_demo_site_image_order", "migrations.add_demo_site_image_order"),
    ("add_demo_site_image_pool_snapshot", "migrations.add_demo_site_image_pool_snapshot"),
    ("add_demo_site_storyblok_collaborator_status", "migrations.add_demo_site_storyblok_collaborator_status"),
    ("add_demo_site_demo_link_sent_at", "migrations.add_demo_site_demo_link_sent_at"),
    ("add_demo_site_storyblok_space_created_at", "migrations.add_demo_site_storyblok_space_created_at"),
    ("add_demo_site_reviewed_at", "migrations.add_demo_site_reviewed_at"),
    ("widen_enrichment_logo_url_to_text", "migrations.widen_enrichment_logo_url_to_text"),
    ("add_push_subscriptions", "migrations.add_push_subscriptions"),
    ("add_notifications_table", "migrations.add_notifications_table"),
    ("add_user_postmaster_oauth", "migrations.add_user_postmaster_oauth"),
    # Charset drift must be repaired before anything compares strings on those tables.
    ("fix_utf8mb4_collation", "migrations.fix_utf8mb4_collation"),
    ("add_email_log_open_tracking", "migrations.add_email_log_open_tracking"),
    ("fix_machine_only_opens", "migrations.fix_machine_only_opens"),
    ("add_campaign_max_emails_per_day", "migrations.add_campaign_max_emails_per_day"),
    ("add_facebook_page_exclusions", "migrations.add_facebook_page_exclusions"),
    ("purge_facebook_page_exclusions", "migrations.purge_facebook_page_exclusions"),
    ("add_demo_site_leads", "migrations.add_demo_site_leads"),
    ("add_sms_tables", "migrations.add_sms_tables"),
    ("add_sms_message_recipient_name", "migrations.add_sms_message_recipient_name"),
    ("add_sms_message_status_detail", "migrations.add_sms_message_status_detail"),
    ("add_sms_config_automation", "migrations.add_sms_config_automation"),
    ("backfill_sms_price_estimate", "migrations.backfill_sms_price_estimate"),
    ("add_email_replies", "migrations.add_email_replies"),
    ("add_reply_conversations", "migrations.add_reply_conversations"),
    ("add_reply_intent", "migrations.add_reply_intent"),
    ("add_email_reply_inbox_forwarded_at", "migrations.add_email_reply_inbox_forwarded_at"),
    ("add_activity_logs_table", "migrations.add_activity_logs_table"),
    ("backfill_activity_from_scraper_diagnostics", "migrations.backfill_activity_from_scraper_diagnostics"),
    ("rebackfill_sms_price_estimate", "migrations.rebackfill_sms_price_estimate"),
    ("add_prospect_do_not_contact", "migrations.add_prospect_do_not_contact"),
    ("add_sms_config_relance_template", "migrations.add_sms_config_relance_template"),
    # Content rewrites run last, once every schema change is in place.
    ("strip_brands_from_subjects", "migrations.strip_brands_from_subjects"),
    ("reseed_email_template_library", "migrations.reseed_email_template_library"),
    ("add_super_admin_and_shared_templates", "migrations.add_super_admin_and_shared_templates"),
    ("add_email_template_forks", "migrations.add_email_template_forks"),
    ("add_campaign_channel", "migrations.add_campaign_channel"),
    ("add_campaign_prospect_position", "migrations.add_campaign_prospect_position"),
    ("nullable_queue_template_id", "migrations.nullable_queue_template_id"),
    ("add_campaign_sms_template_key", "migrations.add_campaign_sms_template_key"),
    ("add_presenter_video_site_seconds", "migrations.add_presenter_video_site_seconds"),
    ("add_user_company_website_url", "migrations.add_user_company_website_url"),
]

# Modules of this package that are not migrations and must not be registered.
_NON_MIGRATION_MODULES: frozenset[str] = frozenset({"__init__", "run_migrations"})


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


def _assert_registry_is_exhaustive() -> None:
    """
    Fail loudly when a migration file exists but is not registered above.

    An unregistered migration is silently never applied: ``init_db()`` creates
    missing tables but never ALTERs an existing one, so the column simply stays
    absent in production and every SELECT on that table 500s. Failing here stops
    the deploy instead, while the schema is still coherent.

    Raises:
        RuntimeError: When at least one migration module is missing from ``MIGRATION_MODULES``.
    """
    on_disk: set[str] = {
        path.stem for path in Path(__file__).resolve().parent.glob("*.py") if path.stem not in _NON_MIGRATION_MODULES
    }
    registered: set[str] = {name for name, _ in MIGRATION_MODULES}
    unregistered: list[str] = sorted(on_disk - registered)
    if unregistered:
        raise RuntimeError(
            "Migration(s) not registered in MIGRATION_MODULES, they would never run: " + ", ".join(unregistered)
        )


def _run_module_migration(module_name: str) -> None:
    module = importlib.import_module(module_name)
    run_migration = getattr(module, "run_migration", None)
    if run_migration is None:
        raise RuntimeError(f"{module_name} must define run_migration()")
    run_migration()


def main() -> None:
    _assert_registry_is_exhaustive()
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
