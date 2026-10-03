"""Who may receive a prospecting SMS: the country rule, then one first contact and one relance.

A prospect is texted only when his country's declared profile opens SMS prospecting (France and
Switzerland). Then the first prospecting message he receives, an email or an SMS, is his first contact;
the next SMS is his relance, and no automated SMS may follow it. The touch of an SMS is read from the
prospect's history, never from the caller: a second SMS campaign sent three days after the first one is
the relance, whatever its template. Each new row writes its touch in ``sms_messages.kind``. A row written
before the touches were told apart (``NULL``) or sent from the manual composer (``prospecting``) ends the
sequence: the former « one SMS per prospect for life » keeps holding for the past, and a manual SMS stops
the automated ones. A send smsmode refused (failed without a provider id) reached nobody and is no touch;
a service message never is one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ColumnElement, Select, and_, or_, select
from sqlalchemy.orm import Session

from enums.sms_message_kind import SmsMessageKind
from enums.sms_status import SmsStatus
from models.email_log import EmailLog
from models.sms_message import SmsMessage
from services.country_profiles import DEFAULT_COUNTRY_CODE, CountryProfiles

if TYPE_CHECKING:
    from models.prospect_db import ProspectDB


class SmsProspectingRules:
    """Decide whether a prospect may receive a prospecting SMS, and which touch it would be."""

    SEQUENCE_COMPLETE: str = (
        "Plus de SMS de prospection pour ce prospect : il a déjà reçu sa relance SMS ou un SMS envoyé à la main"
    )
    NO_FIRST_CONTACT_BEFORE_FOLLOW_UP: str = "Pas de premier contact (email ou SMS) avant cette relance"

    @staticmethod
    def country_of(prospect: ProspectDB) -> str:
        """The prospect's ISO country code, France for a row or a stub that carries none.

        Args:
            prospect: The prospect to read.

        Returns:
            The upper-case ISO code.
        """
        return (getattr(prospect, "country", None) or DEFAULT_COUNTRY_CODE).strip().upper()

    @staticmethod
    def is_country_open(country: str) -> bool:
        """Whether a prospect of *country* may receive a prospecting SMS, as its declared profile states.

        Args:
            country: ISO 3166-1 alpha-2 code, any case.

        Returns:
            ``True`` for France and Switzerland, ``False`` for a closed or undeclared country.
        """
        profile = CountryProfiles.declared(country)
        return profile is not None and profile.sms_prospecting_open

    @classmethod
    def country_refusal(cls, prospect: ProspectDB) -> str | None:
        """Why the prospect's country keeps him out of SMS prospecting, ``None`` when it is open.

        Read from the country's declared profile, never from the default one: ``CountryProfiles.get``
        falls back to France for a closed country, which would open the SMS to Canada by accident.

        Args:
            prospect: The recipient prospect.

        Returns:
            The French refusal, or ``None`` when SMS prospecting is open in his country.
        """
        country = cls.country_of(prospect)
        profile = CountryProfiles.declared(country)
        if profile is None:
            return f"Pays « {country} » inconnu : pas de SMS de prospection"
        if not profile.sms_prospecting_open:
            return f"Pas de SMS de prospection vers ce pays ({profile.label})"
        return None

    @staticmethod
    def _touches_of_user(user_id: int) -> ColumnElement[bool]:
        """The user's prospecting SMS that may have reached their prospect."""
        return and_(
            SmsMessage.user_id == user_id,
            # A NULL prospect id (a self-test SMS) would void every NOT IN built on these rows.
            SmsMessage.prospect_id.isnot(None),
            SmsMessage.kind.is_distinct_from(SmsMessageKind.SERVICE.value),
            or_(SmsMessage.provider_message_id.isnot(None), SmsMessage.status != SmsStatus.FAILED.value),
        )

    @staticmethod
    def _touch_ends_the_sequence() -> ColumnElement[bool]:
        """A touch no automated SMS may follow: a relance, a manual SMS, or a row older than the touches."""
        return or_(
            SmsMessage.kind.is_(None),
            SmsMessage.kind.in_([SmsMessageKind.FOLLOW_UP.value, SmsMessageKind.PROSPECTING.value]),
        )

    @classmethod
    def texted_prospect_ids(cls, user_id: int) -> Select[tuple[int | None]]:
        """The prospects who received a prospecting SMS: none of them may get a cold first contact.

        Args:
            user_id: Owner of the prospects.

        Returns:
            A select of prospect ids, for a ``NOT IN`` filter.
        """
        return select(SmsMessage.prospect_id).where(cls._touches_of_user(user_id))

    @classmethod
    def sequence_complete_prospect_ids(cls, user_id: int) -> Select[tuple[int | None]]:
        """The prospects no automated SMS may reach any more: none of them may get a relance.

        Args:
            user_id: Owner of the prospects.

        Returns:
            A select of prospect ids, for a ``NOT IN`` filter.
        """
        return select(SmsMessage.prospect_id).where(cls._touches_of_user(user_id), cls._touch_ends_the_sequence())

    @classmethod
    def has_received_a_prospecting_sms(cls, db: Session, user_id: int, prospect_id: int) -> bool:
        """Whether the prospect received any prospecting SMS (first contact, relance, manual or older).

        Args:
            db: Active database session.
            user_id: Owner of the prospect.
            prospect_id: The prospect.

        Returns:
            ``True`` when at least one prospecting SMS may have reached him.
        """
        return (
            db.query(SmsMessage.id).filter(cls._touches_of_user(user_id), SmsMessage.prospect_id == prospect_id).first()
            is not None
        )

    @classmethod
    def has_completed_the_sequence(cls, db: Session, user_id: int, prospect_id: int) -> bool:
        """Whether no automated SMS may reach the prospect any more.

        Args:
            db: Active database session.
            user_id: Owner of the prospect.
            prospect_id: The prospect.

        Returns:
            ``True`` once he received his relance SMS, a manual SMS, or an SMS older than the touches.
        """
        return (
            db.query(SmsMessage.id)
            .filter(
                cls._touches_of_user(user_id),
                cls._touch_ends_the_sequence(),
                SmsMessage.prospect_id == prospect_id,
            )
            .first()
            is not None
        )

    @classmethod
    def has_received_a_first_contact(cls, db: Session, user_id: int, prospect_id: int) -> bool:
        """Whether the prospect was contacted once already: an email that left, or a first-contact SMS.

        Args:
            db: Active database session.
            user_id: Owner of the prospect.
            prospect_id: The prospect.

        Returns:
            ``True`` when a relance has a first contact to follow.
        """
        emailed = (
            db.query(EmailLog.id)
            .filter(EmailLog.user_id == user_id, EmailLog.prospect_id == prospect_id, EmailLog.sent_at.isnot(None))
            .first()
        )
        if emailed is not None:
            return True
        texted_first = (
            db.query(SmsMessage.id)
            .filter(
                cls._touches_of_user(user_id),
                SmsMessage.kind == SmsMessageKind.FIRST_CONTACT.value,
                SmsMessage.prospect_id == prospect_id,
            )
            .first()
        )
        return texted_first is not None

    @classmethod
    def next_touch(cls, db: Session, user_id: int, prospect_id: int) -> SmsMessageKind | None:
        """The touch the next prospecting SMS to the prospect would be.

        Args:
            db: Active database session.
            user_id: Owner of the prospect.
            prospect_id: The prospect.

        Returns:
            ``FIRST_CONTACT`` for a prospect never contacted, ``FOLLOW_UP`` after a first contact (email or
            SMS), ``None`` once the sequence is complete.
        """
        if cls.has_completed_the_sequence(db, user_id, prospect_id):
            return None
        if cls.has_received_a_first_contact(db, user_id, prospect_id):
            return SmsMessageKind.FOLLOW_UP
        return SmsMessageKind.FIRST_CONTACT
