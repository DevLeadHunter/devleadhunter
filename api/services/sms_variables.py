"""Personalisation variables of an SMS, resolved once per prospect.

Same trusted sources as the email variables (decision-maker greeting, normalised
trade, dead-website display, configured price) but plain text: no HTML anchor,
and links without their scheme — a bare ``demo.dibodev.fr/slug`` is tapped like
any URL on a phone and costs eight characters less of the single GSM-7 segment.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.prospect_db import ProspectDB
from models.user import User
from services.decision_maker.greeting import build_greeting
from services.email_variables import EmailVariables
from services.pricing_service import PricingService
from services.trade_normalizer import TradeNormalizer


class SmsVariables:
    """Resolves the `{salutation}` / `{entreprise}` / `{lien_demo}`… substitution map of an SMS."""

    SALUTATION = "salutation"
    COMPANY = "entreprise"
    CITY = "ville"
    TRADE = "metier"
    DEMO_LINK = "lien_demo"
    ASSISTANT_LINK = "lien_assistant"
    VIDEO_LINK = "lien_video"
    OLD_WEBSITE = "ancien_site"
    PRICE = "prix"
    SIGNATURE = "signature"

    @staticmethod
    def as_sms_link(url: str | None) -> str:
        """Drop the scheme of a link, keeping its path and query.

        Args:
            url: A full URL, or ``None``.

        Returns:
            The URL without ``https://`` / ``http://``, empty when there is none.
        """
        if not url:
            return ""
        cleaned = url.strip()
        for scheme in ("https://", "http://"):
            if cleaned.startswith(scheme):
                return cleaned[len(scheme) :]
        return cleaned

    @staticmethod
    def signature_for(account_name: str | None) -> str:
        """The sender's first name (first word of the account name), the human sign-off of every SMS.

        Args:
            account_name: The sending user's full name, or ``None``.

        Returns:
            The first name, empty when unknown.
        """
        if not account_name or not account_name.strip():
            return ""
        return account_name.strip().split(" ")[0]

    @classmethod
    def build_for_prospect(
        cls,
        db: Session,
        *,
        user_id: int,
        prospect: ProspectDB,
        demo_url: str = "",
        video_url: str = "",
        sale_price_cents: int | None = None,
    ) -> dict[str, str]:
        """Build the full substitution map for a prospect's SMS.

        Args:
            db: Active database session.
            user_id: The sending user (signature).
            prospect: Prospect being texted.
            demo_url: Full URL of his demo site (rendered without scheme).
            video_url: Full URL of his tracked video page (rendered without scheme).
            sale_price_cents: The sender's website sale price, rendered into {prix}; empty when unset.

        Returns:
            The variable name to value map, ready for template substitution.
        """
        first, last, gender = EmailVariables.resolved_contact(db, prospect.id)
        user: User | None = db.get(User, user_id)
        return {
            cls.SALUTATION: build_greeting(first, last, gender),
            cls.COMPANY: prospect.name or "",
            cls.CITY: prospect.city or "",
            cls.TRADE: TradeNormalizer.normalize(prospect.category),
            cls.DEMO_LINK: cls.as_sms_link(demo_url),
            cls.ASSISTANT_LINK: cls.as_sms_link(EmailVariables.resolve_assistant_url(db, prospect.id)),
            cls.VIDEO_LINK: cls.as_sms_link(video_url),
            cls.OLD_WEBSITE: EmailVariables.display_website(prospect.website),
            cls.PRICE: PricingService.format_price(sale_price_cents) if sale_price_cents is not None else "",
            cls.SIGNATURE: cls.signature_for(user.name if user else None),
        }
