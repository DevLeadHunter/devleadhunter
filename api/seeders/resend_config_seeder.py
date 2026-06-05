"""
Resend config seeder — pre-populate the admin user's ResendConfig from .env.

Reads ``RESEND_API_KEY``, ``RESEND_WEBHOOK_SECRET``, and
``RESEND_FROM_EMAIL`` / ``RESEND_FROM_NAME`` from the environment and stores
them encrypted in the ``resend_config`` table for the admin user.

Safe to re-run: existing rows are updated in place.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def seed_resend_config() -> None:
    """
    Upsert the admin user's Resend configuration from environment variables.

    Skipped silently when ``RESEND_API_KEY`` is not set (so the seeder
    doesn't block CI or fresh installs without Resend credentials).
    """
    from sqlalchemy import select
    from core.config import settings
    from core.database import get_db, init_db
    from models.resend_config import ResendConfig
    from models.user import User
    from services.encryption_service import encryption_service

    init_db()
    db = next(get_db())

    try:
        api_key: str = getattr(settings, "resend_api_key", "")
        if not api_key:
            print("[SKIP] RESEND_API_KEY not set — skipping ResendConfig seeder")
            return

        # Locate the admin user
        admin: User | None = db.execute(
            select(User).where(User.email == settings.admin_email)
        ).scalar_one_or_none()

        if admin is None:
            print(f"[SKIP] Admin user {settings.admin_email!r} not found — run user seeder first")
            return

        # Upsert the config row
        config: ResendConfig | None = db.execute(
            select(ResendConfig).where(ResendConfig.user_id == admin.id)
        ).scalar_one_or_none()

        if config is None:
            config = ResendConfig(user_id=admin.id)
            db.add(config)

        config.api_key = encryption_service.encrypt(api_key)

        webhook_secret: str = getattr(settings, "resend_webhook_secret", "")
        config.webhook_secret = encryption_service.encrypt(webhook_secret) if webhook_secret else None

        # from_email / from_name can be set via optional env vars
        import os
        config.from_email = os.environ.get("RESEND_FROM_EMAIL", f"leo@mail.dibodev.fr")
        config.from_name  = os.environ.get("RESEND_FROM_NAME", admin.name)

        db.commit()
        print(f"[OK] ResendConfig seeded for admin user {settings.admin_email!r}")

    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] ResendConfig seeder failed: {exc}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_resend_config()
