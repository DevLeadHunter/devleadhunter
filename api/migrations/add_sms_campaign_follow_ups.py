"""Let an SMS campaign carry its relance and its results like an email campaign.

- ``campaign_follow_ups.template_id`` becomes nullable and ``sms_template_key`` is added: an SMS
  campaign's relance step names a template of the SMS library instead of an email template.
- ``email_queue.sms_template_key`` (the template an SMS follow-up renders) and
  ``email_queue.sms_message_id`` (the SMS an item sent, whose delivery report and cost feed the
  results) are added. The sent rows of the existing SMS campaigns are linked to their SMS: the first
  SMS of the same user and prospect written within a day of the row's slot.
- ``sms_replies.intent`` stores the verdict of an SMS reply, as ``email_replies.intent`` does.

Every column is checked against INFORMATION_SCHEMA before its ALTER: prod and local schemas diverge.
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine

_LINK_EARLIEST_OFFSET = timedelta(minutes=10)
_LINK_LATEST_OFFSET = timedelta(days=1)


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


def _column_is_nullable(connection: Connection, table_name: str, column_name: str) -> bool:
    """Whether the column already accepts NULL."""
    result = connection.execute(
        text(
            """
            SELECT IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table_name
              AND COLUMN_NAME = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar() == "YES"


def _make_follow_up_template_nullable(connection: Connection) -> None:
    """Drop the template foreign key, let the column take NULL, and put the key back."""
    foreign_key_name = connection.execute(
        text(
            """
            SELECT CONSTRAINT_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'campaign_follow_ups'
              AND COLUMN_NAME = 'template_id'
              AND REFERENCED_TABLE_NAME = 'email_templates'
            LIMIT 1
            """
        )
    ).scalar()
    if foreign_key_name:
        connection.execute(text(f"ALTER TABLE campaign_follow_ups DROP FOREIGN KEY `{foreign_key_name}`"))
    connection.execute(text("ALTER TABLE campaign_follow_ups MODIFY COLUMN template_id INT NULL"))
    connection.execute(
        text(
            "ALTER TABLE campaign_follow_ups ADD CONSTRAINT fk_campaign_follow_ups_template "
            "FOREIGN KEY (template_id) REFERENCES email_templates(id) ON DELETE RESTRICT"
        )
    )


def _link_sent_sms_rows(connection: Connection) -> int:
    """Link the sent rows of the existing SMS campaigns to the SMS they wrote; returns how many were linked."""
    rows = connection.execute(
        text(
            """
            SELECT email_queue.id, email_queue.user_id, email_queue.prospect_id, email_queue.scheduled_at
            FROM email_queue
            JOIN campaigns ON campaigns.id = email_queue.campaign_id
            WHERE campaigns.channel = 'sms'
              AND email_queue.status = 'sent'
              AND email_queue.sms_message_id IS NULL
            ORDER BY email_queue.scheduled_at
            """
        )
    ).all()
    linked_message_ids: set[int] = set(
        connection.execute(text("SELECT sms_message_id FROM email_queue WHERE sms_message_id IS NOT NULL"))
        .scalars()
        .all()
    )
    linked_rows: int = 0
    for queue_id, user_id, prospect_id, scheduled_at in rows:
        candidate_ids = (
            connection.execute(
                text(
                    """
                    SELECT id
                    FROM sms_messages
                    WHERE user_id = :user_id
                      AND prospect_id = :prospect_id
                      AND created_at >= :earliest
                      AND created_at < :latest
                    ORDER BY created_at
                    """
                ),
                {
                    "user_id": user_id,
                    "prospect_id": prospect_id,
                    "earliest": scheduled_at - _LINK_EARLIEST_OFFSET,
                    "latest": scheduled_at + _LINK_LATEST_OFFSET,
                },
            )
            .scalars()
            .all()
        )
        message_id = next((candidate for candidate in candidate_ids if candidate not in linked_message_ids), None)
        if message_id is None:
            continue
        connection.execute(
            text("UPDATE email_queue SET sms_message_id = :message_id WHERE id = :queue_id"),
            {"message_id": message_id, "queue_id": queue_id},
        )
        linked_message_ids.add(message_id)
        linked_rows += 1
    return linked_rows


def run_migration() -> None:
    """Add the missing columns, then link the sent SMS rows (re-runnable)."""
    with engine.connect() as connection:
        if not _column_is_nullable(connection, "campaign_follow_ups", "template_id"):
            _make_follow_up_template_nullable(connection)
        if not _column_exists(connection, "campaign_follow_ups", "sms_template_key"):
            connection.execute(text("ALTER TABLE campaign_follow_ups ADD COLUMN sms_template_key VARCHAR(64) NULL"))
        if not _column_exists(connection, "email_queue", "sms_template_key"):
            connection.execute(text("ALTER TABLE email_queue ADD COLUMN sms_template_key VARCHAR(64) NULL"))
        if not _column_exists(connection, "email_queue", "sms_message_id"):
            connection.execute(text("ALTER TABLE email_queue ADD COLUMN sms_message_id INT NULL"))
            connection.execute(text("CREATE INDEX ix_email_queue_sms_message_id ON email_queue (sms_message_id)"))
        if not _column_exists(connection, "sms_replies", "intent"):
            connection.execute(text("ALTER TABLE sms_replies ADD COLUMN intent VARCHAR(32) NULL"))
        linked_rows = _link_sent_sms_rows(connection)
        connection.commit()
    print(f"  ~ {linked_rows} sent SMS row(s) linked to their SMS")


if __name__ == "__main__":
    run_migration()
    print("SMS campaign follow-ups and results columns ensured.")
