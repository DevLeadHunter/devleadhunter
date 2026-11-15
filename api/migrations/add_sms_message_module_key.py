"""File each SMS under the module that sent it: add ``sms_messages.module_key`` and fill it for the SMS already sent.

An SMS of a campaign takes the module of the library template its queue row names, as the campaign engine reads it.
Any other SMS takes the module whose links or service messages it carries, when a module claims it. The rest stays
with the websites module.

Re-runnable.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, select, text, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine
from core.product_modules.contract import WEBSITES_MODULE_KEY
from models.campaign import Campaign
from models.email_queue import EmailQueue
from models.sms_message import SmsMessage
from services.campaign_offers import CampaignOffers
from services.sms.templates import find_sms_template

_TABLE: str = "sms_messages"
_COLUMN: str = "module_key"
_INDEX: str = "ix_sms_messages_module_key"


def run_migration(target_engine: Engine = engine) -> None:
    """Add the column and its index when missing, then file the SMS already sent under their module."""
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
        for message in db.execute(select(SmsMessage)).scalars():
            claiming_module_key: str | None = CampaignOffers.module_key_of_sms(message)
            if claiming_module_key is not None:
                message.module_key = claiming_module_key
        campaign_sends = db.execute(
            select(EmailQueue.sms_message_id, EmailQueue.sms_template_key, Campaign.sms_template_key)
            .join(Campaign, Campaign.id == EmailQueue.campaign_id)
            .where(EmailQueue.sms_message_id.is_not(None))
        ).all()
        for sms_message_id, follow_up_template_key, first_contact_template_key in campaign_sends:
            template = find_sms_template(follow_up_template_key or first_contact_template_key or "")
            module_key: str = CampaignOffers.sms_template_module(template)
            if module_key != WEBSITES_MODULE_KEY:
                db.execute(update(SmsMessage).where(SmsMessage.id == sms_message_id).values(module_key=module_key))
        db.commit()


if __name__ == "__main__":
    run_migration()
    print("sms_messages.module_key ensured and filled for the SMS already sent.")
