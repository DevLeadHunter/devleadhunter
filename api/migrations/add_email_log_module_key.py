"""File each sent email under the module that sent it: add ``email_logs.module_key`` and fill it for the emails sent.

An email of a campaign takes the campaign's module, read from its templates as the campaign engine reads it. An email
that a module's own table names in an ``email_log_id`` column takes that module. Every other email written before
this column existed stays with the websites module.

Re-runnable.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import FromClause, inspect, select, text, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import Base, engine
from core.product_modules.contract import WEBSITES_MODULE_KEY, ProductModule
from core.product_modules.registry import product_module_registry
from models.campaign import Campaign
from models.email_log import EmailLog
from services.campaign_queue_service import CampaignQueueService

_TABLE: str = "email_logs"
_COLUMN: str = "module_key"
_INDEX: str = "ix_email_logs_module_key"
_SENT_EMAIL_COLUMN: str = "email_log_id"


def run_migration(target_engine: Engine = engine) -> None:
    """Add the column and its index when missing, then file the emails already sent under their module."""
    inspector = inspect(target_engine)
    existing_columns: set[str] = {column["name"] for column in inspector.get_columns(_TABLE)}
    existing_indexes: set[str | None] = {index["name"] for index in inspector.get_indexes(_TABLE)}
    with target_engine.connect() as conn:
        if _COLUMN not in existing_columns:
            conn.execute(
                text(f"ALTER TABLE {_TABLE} ADD COLUMN {_COLUMN} VARCHAR(64) NOT NULL DEFAULT '{WEBSITES_MODULE_KEY}'")
            )
        if _INDEX not in existing_indexes:
            conn.execute(text(f"CREATE INDEX {_INDEX} ON {_TABLE} ({_COLUMN})"))
        conn.commit()
    with Session(target_engine) as db:
        queue_service = CampaignQueueService(db)
        email_campaigns = db.execute(select(Campaign).where(Campaign.channel != "sms")).scalars().all()
        for campaign in email_campaigns:
            module_key: str = queue_service.email_campaign_module_key(campaign)
            if module_key != WEBSITES_MODULE_KEY:
                db.execute(update(EmailLog).where(EmailLog.campaign_id == campaign.id).values(module_key=module_key))
        for module in product_module_registry.installed():
            for table in _tables_naming_a_sent_email(module):
                sent_email_ids = select(table.c[_SENT_EMAIL_COLUMN]).where(table.c[_SENT_EMAIL_COLUMN].is_not(None))
                db.execute(
                    update(EmailLog)
                    .where(EmailLog.id.in_(sent_email_ids))
                    .values(module_key=module.key)
                    .execution_options(synchronize_session=False)
                )
        db.commit()


def _tables_naming_a_sent_email(module: ProductModule) -> list[FromClause]:
    """
    The module's own tables whose rows name the email they sent.

    Args:
        module: An installed product module, its models loaded.

    Returns:
        The tables of the module's package that have an ``email_log_id`` column.
    """
    package: str = type(module).__module__.partition(".")[0]
    return [
        mapper.local_table
        for mapper in Base.registry.mappers
        if mapper.class_.__module__.partition(".")[0] == package and _SENT_EMAIL_COLUMN in mapper.local_table.c
    ]


if __name__ == "__main__":
    run_migration()
    print("email_logs.module_key ensured and filled for the emails already sent.")
