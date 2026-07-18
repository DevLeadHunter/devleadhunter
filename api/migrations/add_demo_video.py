"""Add prospection-video columns to demo_sites + presenter_videos table."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine


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
        if not _column_exists(conn, "demo_sites", "video_status"):
            conn.execute(
                text(
                    """
                    ALTER TABLE demo_sites
                    ADD COLUMN video_status VARCHAR(32) NULL,
                    ADD COLUMN video_error TEXT NULL,
                    ADD COLUMN video_generated_at DATETIME NULL,
                    ADD INDEX ix_demo_sites_video_status (video_status)
                    """
                )
            )

        # Table also created by init_db() on fresh databases; kept here for
        # existing databases upgraded in place.
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS presenter_videos (
                  id INT NOT NULL AUTO_INCREMENT,
                  user_id INT NOT NULL,
                  file_path VARCHAR(512) NOT NULL,
                  original_filename VARCHAR(255) NULL,
                  duration_seconds FLOAT NOT NULL DEFAULT 0,
                  intro_seconds FLOAT NOT NULL DEFAULT 4,
                  outro_seconds FLOAT NOT NULL DEFAULT 5,
                  auto_generate TINYINT(1) NOT NULL DEFAULT 1,
                  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at DATETIME NULL,
                  PRIMARY KEY (id),
                  UNIQUE KEY ix_presenter_videos_user_id (user_id),
                  CONSTRAINT fk_presenter_videos_user_id
                    FOREIGN KEY (user_id) REFERENCES users (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
        )
        conn.commit()


if __name__ == "__main__":
    run_migration()
