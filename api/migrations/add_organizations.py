"""Add organizations + organization_members tables and sharing/reservation columns on prospects."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine


def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table_name
            """
        ),
        {"table_name": table_name},
    )
    return bool(result.scalar())


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(
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


def run_migration() -> None:
    with engine.connect() as conn:
        if not _table_exists(conn, "organizations"):
            conn.execute(
                text(
                    """
                    CREATE TABLE organizations (
                        id INT NOT NULL AUTO_INCREMENT,
                        name VARCHAR(255) NOT NULL,
                        owner_user_id INT NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        INDEX ix_organizations_owner_user_id (owner_user_id),
                        CONSTRAINT fk_organizations_owner
                            FOREIGN KEY (owner_user_id) REFERENCES users (id)
                            ON DELETE CASCADE
                    )
                    """
                )
            )

        if not _table_exists(conn, "organization_members"):
            conn.execute(
                text(
                    """
                    CREATE TABLE organization_members (
                        id INT NOT NULL AUTO_INCREMENT,
                        organization_id INT NOT NULL,
                        user_id INT NOT NULL,
                        role VARCHAR(20) NOT NULL DEFAULT 'member',
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        UNIQUE KEY uq_organization_members_user_id (user_id),
                        INDEX ix_organization_members_organization_id (organization_id),
                        CONSTRAINT fk_org_members_org
                            FOREIGN KEY (organization_id) REFERENCES organizations (id)
                            ON DELETE CASCADE,
                        CONSTRAINT fk_org_members_user
                            FOREIGN KEY (user_id) REFERENCES users (id)
                            ON DELETE CASCADE
                    )
                    """
                )
            )

        if not _column_exists(conn, "prospects", "organization_id"):
            conn.execute(
                text(
                    """
                    ALTER TABLE prospects
                    ADD COLUMN organization_id INT NULL,
                    ADD INDEX ix_prospects_organization_id (organization_id)
                    """
                )
            )

        if not _column_exists(conn, "prospects", "reserved_by_user_id"):
            conn.execute(
                text(
                    """
                    ALTER TABLE prospects
                    ADD COLUMN reserved_by_user_id INT NULL,
                    ADD COLUMN reserved_at DATETIME NULL,
                    ADD INDEX ix_prospects_reserved_by_user_id (reserved_by_user_id)
                    """
                )
            )

        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("organizations tables and prospects sharing columns ensured.")
