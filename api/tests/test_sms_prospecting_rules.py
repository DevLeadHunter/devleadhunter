"""One first contact and one relance per prospect, read from his history.

The first prospecting message a prospect receives (email or SMS) is his first contact, the next SMS his
relance, and nothing automated follows. A legacy row and a manual SMS end the sequence; a send smsmode
refused reached nobody and counts for nothing.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from enums.sms_message_kind import SmsMessageKind
from models.demo_site import DemoSite
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from models.sms_message import SmsMessage
from services.sms_automation_service import sms_automation_service
from services.sms_prospecting_rules import SmsProspectingRules
from services.sms_relance_service import sms_relance_service

_USER_ID = 7
_NOW: datetime = datetime.now(UTC).replace(tzinfo=None)


def _prospect(
    db: Session, *, name: str, slug: str, email: str | None = None, contacted: bool = False, country: str = "FR"
) -> ProspectDB:
    """A prospect with a mobile of his country and a live demo."""
    prospect = ProspectDB(
        user_id=_USER_ID,
        name=name,
        category="Garage",
        source="google_maps",
        phone="06 12 34 56 78" if country == "FR" else "079 123 45 67",
        email=email,
        contacted=contacted,
        country=country,
    )
    db.add(prospect)
    db.flush()
    db.add(
        DemoSite(
            user_id=_USER_ID,
            prospect_id=prospect.id,
            slug=slug,
            business_name=name,
            status="active",
            expires_at=datetime.now(UTC) + timedelta(days=10),
        )
    )
    db.commit()
    return prospect


def _email(db: Session, prospect: ProspectDB, *, days_ago: int, replied: bool = False) -> None:
    db.add(
        EmailLog(
            user_id=_USER_ID,
            prospect_id=prospect.id,
            recipient_email=prospect.email or "garage@example.com",
            subject="Votre site",
            body_html="<p>Bonjour</p>",
            provider="resend",
            status="sent",
            sent_at=_NOW - timedelta(days=days_ago),
            replied_at=_NOW - timedelta(days=days_ago - 1) if replied else None,
        )
    )
    db.commit()


def _sms(
    db: Session,
    prospect: ProspectDB,
    *,
    kind: str | None,
    days_ago: int = 2,
    status: str = "sent",
    provider_message_id: str | None = "provider-id",
) -> None:
    db.add(
        SmsMessage(
            user_id=_USER_ID,
            prospect_id=prospect.id,
            to_e164="+33612345678",
            sender="Dibodev",
            body="Bonjour",
            status=status,
            segments=1,
            kind=kind,
            provider_message_id=provider_message_id,
            created_at=_NOW - timedelta(days=days_ago),
        )
    )
    db.commit()


def _relance_candidate_ids(db: Session) -> set[int]:
    return {candidate.prospect.id for candidate in sms_relance_service.find_candidates(db, _USER_ID, after_days=30)}


class TestNextTouch:
    def test_a_prospect_never_contacted_gets_a_first_contact(self, db: Session) -> None:
        prospect = _prospect(db, name="Garage Martin", slug="garage-martin")

        assert SmsProspectingRules.next_touch(db, _USER_ID, prospect.id) is SmsMessageKind.FIRST_CONTACT

    def test_the_sms_after_a_first_contact_sms_is_the_relance(self, db: Session) -> None:
        prospect = _prospect(db, name="Garage Martin", slug="garage-martin")
        _sms(db, prospect, kind=SmsMessageKind.FIRST_CONTACT.value)

        assert SmsProspectingRules.next_touch(db, _USER_ID, prospect.id) is SmsMessageKind.FOLLOW_UP

    def test_the_first_sms_after_an_email_is_the_relance(self, db: Session) -> None:
        prospect = _prospect(db, name="Plomberie Vidal", slug="plomberie-vidal", email="vidal@example.com")
        _email(db, prospect, days_ago=4)

        assert SmsProspectingRules.next_touch(db, _USER_ID, prospect.id) is SmsMessageKind.FOLLOW_UP

    def test_nothing_follows_the_relance(self, db: Session) -> None:
        prospect = _prospect(db, name="Garage Martin", slug="garage-martin")
        _sms(db, prospect, kind=SmsMessageKind.FIRST_CONTACT.value, days_ago=3)
        _sms(db, prospect, kind=SmsMessageKind.FOLLOW_UP.value)

        assert SmsProspectingRules.next_touch(db, _USER_ID, prospect.id) is None

    def test_a_legacy_row_and_a_manual_sms_end_the_sequence(self, db: Session) -> None:
        """The former « one SMS per prospect for life » keeps holding for the rows written before the touches."""
        legacy = _prospect(db, name="Garage Martin", slug="garage-martin")
        _sms(db, legacy, kind=None)
        manual = _prospect(db, name="Plomberie Vidal", slug="plomberie-vidal")
        _sms(db, manual, kind=SmsMessageKind.PROSPECTING.value)

        assert SmsProspectingRules.next_touch(db, _USER_ID, legacy.id) is None
        assert SmsProspectingRules.next_touch(db, _USER_ID, manual.id) is None

    def test_a_send_smsmode_refused_is_no_touch(self, db: Session) -> None:
        refused = _prospect(db, name="Garage Martin", slug="garage-martin")
        _sms(db, refused, kind=SmsMessageKind.FIRST_CONTACT.value, status="failed", provider_message_id=None)
        undelivered = _prospect(db, name="Plomberie Vidal", slug="plomberie-vidal")
        _sms(db, undelivered, kind=SmsMessageKind.FIRST_CONTACT.value, status="failed")

        assert SmsProspectingRules.next_touch(db, _USER_ID, refused.id) is SmsMessageKind.FIRST_CONTACT
        # Accepted then reported undelivered: it may have reached the phone, so it stays a first contact.
        assert SmsProspectingRules.next_touch(db, _USER_ID, undelivered.id) is SmsMessageKind.FOLLOW_UP

    def test_a_service_sms_is_no_touch(self, db: Session) -> None:
        prospect = _prospect(db, name="Garage Martin", slug="garage-martin")
        _sms(db, prospect, kind=SmsMessageKind.SERVICE.value)

        assert SmsProspectingRules.has_received_a_prospecting_sms(db, _USER_ID, prospect.id) is False
        assert SmsProspectingRules.next_touch(db, _USER_ID, prospect.id) is SmsMessageKind.FIRST_CONTACT


class TestSelections:
    def test_an_emailed_prospect_stays_a_relance_candidate_until_his_relance(self, db: Session) -> None:
        emailed = _prospect(db, name="Plomberie Vidal", slug="plomberie-vidal", email="vidal@example.com")
        _email(db, emailed, days_ago=40)
        relanced = _prospect(db, name="Garage Martin", slug="garage-martin", email="martin@example.com")
        _email(db, relanced, days_ago=40)
        _sms(db, relanced, kind=SmsMessageKind.FOLLOW_UP.value)
        replied = _prospect(db, name="Garage Durand", slug="garage-durand", email="durand@example.com")
        _email(db, replied, days_ago=40, replied=True)

        assert _relance_candidate_ids(db) == {emailed.id}

    def test_a_prospect_texted_first_is_not_offered_to_the_email_relance(self, db: Session) -> None:
        """The J+30 relance and its page recall an email: a prospect never emailed gets his relance by campaign."""
        texted = _prospect(db, name="Garage Martin", slug="garage-martin", contacted=True)
        _sms(db, texted, kind=SmsMessageKind.FIRST_CONTACT.value, days_ago=40)

        assert _relance_candidate_ids(db) == set()

    def test_the_cold_selection_leaves_out_any_prospect_already_texted(self, db: Session) -> None:
        fresh = _prospect(db, name="Garage Martin", slug="garage-martin")
        texted = _prospect(db, name="Plomberie Vidal", slug="plomberie-vidal")
        _sms(db, texted, kind=SmsMessageKind.FIRST_CONTACT.value)
        refused = _prospect(db, name="Garage Durand", slug="garage-durand")
        _sms(db, refused, kind=SmsMessageKind.FIRST_CONTACT.value, status="failed", provider_message_id=None)

        cold_ids = {candidate.prospect.id for candidate in sms_relance_service.find_cold_candidates(db, _USER_ID)}

        assert cold_ids == {fresh.id, refused.id}

    def test_a_belgian_prospect_is_never_selected(self, db: Session) -> None:
        belgian = _prospect(db, name="Garage Peeters", slug="garage-peeters", country="BE")
        belgian.phone = "0470 12 34 56"
        db.commit()

        assert sms_relance_service.find_cold_candidates(db, _USER_ID) == []


class TestAutomationReasons:
    def test_the_automation_names_what_blocks_a_planned_sms(self, db: Session) -> None:
        texted = _prospect(db, name="Garage Martin", slug="garage-martin", contacted=True)
        _sms(db, texted, kind=SmsMessageKind.FIRST_CONTACT.value, days_ago=10)

        assert sms_automation_service._ineligibility_reason(db, _USER_ID, texted, "cold") == "Déjà contacté par SMS"
        assert sms_automation_service._ineligibility_reason(db, _USER_ID, texted, "relance") is None
        _sms(db, texted, kind=SmsMessageKind.FOLLOW_UP.value)
        assert sms_automation_service._ineligibility_reason(db, _USER_ID, texted, "relance") == (
            "Déjà relancé par SMS (ou SMS envoyé à la main)"
        )

    def test_a_closed_country_is_named_as_the_reason(self, db: Session) -> None:
        belgian = _prospect(db, name="Garage Peeters", slug="garage-peeters", country="BE")

        assert sms_automation_service._ineligibility_reason(db, _USER_ID, belgian, "cold") == (
            "Pas de SMS de prospection vers ce pays (Belgique)"
        )
