"""Personalisation variables of an SMS, resolved once per prospect.

Same trusted sources as the email variables (decision-maker greeting, normalised
trade, dead-website display, configured price) but plain text: no HTML anchor,
and links without their scheme — a bare ``demo.dibodev.fr/slug`` is tapped like
any URL on a phone and costs eight characters less of the GSM-7 budget. The
``{telephone}`` variable is the sender's public phone (``users.contact_phone``, the
one shown on the demo banner): the alphanumeric SMS sender receives no reply, so a
frank SMS names the number to answer to.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.ai_assistant import AiAssistant
from models.prospect_db import ProspectDB
from models.user import User
from services.ai_assistant.assistant_service import ai_assistant_service
from services.ai_assistant.receptionist_wording import ReceptionistWording
from services.assistant_pricing_service import AssistantPricingService
from services.country_profiles import DEFAULT_COUNTRY_CODE, CountryProfile, CountryProfiles
from services.decision_maker.greeting import build_greeting
from services.email_variables import EmailVariables
from services.regional_lexicon import RegionalLexicon
from services.sms.phone_normalizer import format_phone_for_reader
from services.tracking_links import sms_tracked_link
from services.trade_normalizer import TradeNormalizer


class SmsVariables:
    """Resolves the `{salutation}` / `{entreprise}` / `{lien_demo}`… substitution map of an SMS."""

    SALUTATION = "salutation"
    COMPANY = "entreprise"
    CITY = "ville"
    TRADE = "metier"
    DEMO_LINK = "lien_demo"
    ASSISTANT_LINK = "lien_assistant"
    RECEPTIONIST_FIRST_NAME = "prenom_receptionniste"
    RECEPTIONIST = "receptionniste"
    VIRTUAL_ASSISTANT = "assistant_virtuel"
    VIDEO_LINK = "lien_video"
    ASSISTANT_VIDEO_LINK = "lien_video_assistant"
    OLD_WEBSITE = "ancien_site"
    PRICE = "prix"
    PRICE_ASSISTANT = "prix_assistant"
    PHONE = "telephone"
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
    def phone_for(contact_phone: str | None, reader_country: str | None = DEFAULT_COUNTRY_CODE) -> str:
        """The sender's public phone as the prospect must dial it, the number he answers to.

        The sender's number is read as a French one unless written in international form; a prospect
        abroad gets it in international form (« +33 6 12 34 56 78 »), a French one in national form.

        Args:
            contact_phone: The sending user's ``contact_phone``, or ``None``.
            reader_country: ISO code of the prospect's country.

        Returns:
            The phone to print; empty when the user has not set one (a template using
            ``{telephone}`` must not be sent then).
        """
        return format_phone_for_reader(
            contact_phone, number_country=DEFAULT_COUNTRY_CODE, reader_country=reader_country
        )

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
        assistant: AiAssistant | None,
        demo_url: str = "",
        video_url: str = "",
        sale_price_cents: int | None = None,
    ) -> dict[str, str]:
        """Build the full substitution map for a prospect's SMS.

        The receptionist's links take the SMS short form, as the callers give the site's. The prices
        are written as the prospect reads them in his country (« 500 € », « ≈ 470 CHF », which the GSM-7
        transliteration of the body turns into « env. 470 CHF »).

        Args:
            db: Active database session.
            user_id: The sending user (signature).
            prospect: Prospect being texted.
            assistant: The sender's active assistant for him (``ai_assistant_service.get_active_for_prospect``), or None.
            demo_url: Full URL of his demo site (rendered without scheme).
            video_url: Full URL of his tracked video page (rendered without scheme).
            sale_price_cents: The sender's website sale price in euro cents, rendered into {prix}; empty when unset.

        Returns:
            The variable name to value map, ready for template substitution.
        """
        first, last, gender = EmailVariables.resolved_contact(db, prospect.id)
        user: User | None = db.get(User, user_id)
        assistant_url: str = ai_assistant_service.page_url(assistant.slug) if assistant is not None else ""
        assistant_video_url: str = EmailVariables.assistant_video_urls(assistant)[0]
        country: CountryProfile = CountryProfiles.get(prospect.country)
        return {
            cls.SALUTATION: build_greeting(first, last, gender),
            cls.COMPANY: prospect.name or "",
            cls.CITY: prospect.city or "",
            cls.TRADE: TradeNormalizer.normalize(prospect.category),
            cls.DEMO_LINK: cls.as_sms_link(demo_url),
            cls.ASSISTANT_LINK: cls.as_sms_link(sms_tracked_link(assistant_url)) if assistant_url else "",
            cls.RECEPTIONIST_FIRST_NAME: assistant.assistant_name if assistant is not None else "",
            cls.RECEPTIONIST: ReceptionistWording.receptionist(assistant),
            cls.VIRTUAL_ASSISTANT: ReceptionistWording.virtual_assistant(assistant),
            cls.VIDEO_LINK: cls.as_sms_link(video_url),
            cls.ASSISTANT_VIDEO_LINK: (
                cls.as_sms_link(sms_tracked_link(assistant_video_url)) if assistant_video_url else ""
            ),
            cls.OLD_WEBSITE: EmailVariables.display_website(prospect.website),
            cls.PRICE: country.format_price(sale_price_cents) if sale_price_cents is not None else "",
            # Resolved from user_id (the assistant monthly price is per-user, like {prix}).
            cls.PRICE_ASSISTANT: country.format_price(AssistantPricingService.monthly_price_cents(db, user_id)),
            cls.PHONE: cls.phone_for(user.contact_phone if user else None, country.code),
            RegionalLexicon.COUNTRY_KEY: country.code,
            cls.SIGNATURE: cls.signature_for(user.name if user else None),
        }
