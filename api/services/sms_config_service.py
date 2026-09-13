"""Per-user SMS configuration — the alphanumeric sender + enable flag."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from enums.sms_template_category import SmsTemplateCategory
from models.sms_config import SmsConfig
from services.sms.templates import find_sms_template

# Alphanumeric sender: letters/digits/spaces, 3–11 chars, at least one letter
# (French A2P rule; a purely numeric sender is not a valid alphanumeric OADC).
_SENDER_RE: re.Pattern[str] = re.compile(r"^(?=.*[A-Za-z])[A-Za-z0-9 ]{3,11}$")


class SmsConfigService:
    """Read/write a user's SMS sender identity."""

    def get(self, db: Session, user_id: int) -> SmsConfig | None:
        """Return the user's SMS config, or ``None`` when never set.

        Args:
            db: Active database session.
            user_id: Owner.

        Returns:
            The config row, or ``None``.
        """
        return db.query(SmsConfig).filter(SmsConfig.user_id == user_id).first()

    @staticmethod
    def is_valid_sender(sender: str) -> bool:
        """Whether *sender* is a valid French alphanumeric sender id.

        Args:
            sender: Candidate sender.

        Returns:
            ``True`` when 3–11 chars, alphanumeric/space, with at least one letter.
        """
        return bool(_SENDER_RE.match(sender or ""))

    def upsert(self, db: Session, user_id: int, *, sender: str) -> SmsConfig:
        """Create or update the user's SMS sender (the channel's only switch).

        A non-empty, valid sender turns the channel on; an empty sender clears it.

        Args:
            db: Active database session.
            user_id: Owner.
            sender: Alphanumeric sender id (empty to disable the channel).

        Returns:
            The persisted config.

        Raises:
            ValueError: When *sender* is non-empty and invalid.
        """
        cleaned = (sender or "").strip()
        if cleaned and not self.is_valid_sender(cleaned):
            raise ValueError("Expéditeur invalide : 3 à 11 caractères, lettres/chiffres, au moins une lettre.")
        config = self.get(db, user_id)
        if config is None:
            config = SmsConfig(user_id=user_id)
            db.add(config)
        config.sender = cleaned
        # A configured sender is the on/off switch; keep the legacy column consistent.
        config.enabled = bool(cleaned)
        db.commit()
        db.refresh(config)
        return config

    def set_automation(
        self,
        db: Session,
        user_id: int,
        *,
        cold_sms_enabled: bool,
        auto_relance_enabled: bool,
        auto_relance_after_days: int,
        relance_template_key: str | None = None,
    ) -> SmsConfig:
        """Update the user's SMS automation opt-ins (get-or-create the config row).

        Args:
            db: Active database session.
            user_id: Owner.
            cold_sms_enabled: Cold-SMS prospects who have a mobile but no email.
            auto_relance_enabled: Auto-relance emailed prospects who never reacted.
            auto_relance_after_days: Delay (days) before the auto-relance fires (clamped 7–120).
            relance_template_key: Library template the J+30 relance renders; ``None`` keeps the current one.

        Returns:
            The persisted config.

        Raises:
            ValueError: When *relance_template_key* is not a follow-up template of the library.
        """
        if relance_template_key is not None:
            template = find_sms_template(relance_template_key)
            if template is None or template.category is not SmsTemplateCategory.FOLLOW_UP:
                raise ValueError("Modèle de relance inconnu : choisissez un modèle de relance de la bibliothèque.")
        config = self.get(db, user_id)
        if config is None:
            config = SmsConfig(user_id=user_id)
            db.add(config)
        config.cold_sms_enabled = cold_sms_enabled
        config.auto_relance_enabled = auto_relance_enabled
        config.auto_relance_after_days = max(7, min(int(auto_relance_after_days), 120))
        if relance_template_key is not None:
            config.relance_template_key = relance_template_key
        db.commit()
        db.refresh(config)

        # Local import: the system-campaign service is fed by this config, never the reverse.
        from services.sms_auto_campaign_service import sms_auto_campaign_service

        sms_auto_campaign_service.sync_automation(
            db, user_id, enabled=auto_relance_enabled, template_key=config.relance_template_key
        )
        return config


sms_config_service = SmsConfigService()
