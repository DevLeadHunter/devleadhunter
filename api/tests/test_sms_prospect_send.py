"""A prospect SMS: open countries only, his own numbering, smsmode's opt-out mention, two segments at most.

The sending guards are tested with fixture templates rather than the library's: the library's copy
changes on its own schedule, and this file is about the sending service, not the wording.
"""

import asyncio
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy.orm import Session

import services.sms_service as sms_module
from core.config import settings
from enums.sms_message_kind import SmsMessageKind
from enums.sms_template_category import SmsTemplateCategory
from models.ai_assistant import AiAssistant
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from models.sms_config import SmsConfig
from models.sms_message import SmsMessage
from services.ai_assistant.assistant_service import ai_assistant_service
from services.sms.send_window import SmsSendWindow
from services.sms.sms_provider import SmsSendResult
from services.sms.templates import SmsTemplate
from services.sms_prospecting_rules import SmsProspectingRules
from services.sms_service import SmsService
from services.sms_variables import SmsVariables
from tests.assistant_fakes import AcceptingSmsProvider, AsyncCallRecorder

_USER_ID = 7
_FIXTURE_TEMPLATES: dict[str, SmsTemplate] = {
    "direct": SmsTemplate(
        key="direct",
        name="Direct",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body="{salutation}, j'ai préparé un site pour {entreprise}, il est déjà en ligne : {lien_demo} {signature}",
    ),
    "rappel-court": SmsTemplate(
        key="rappel-court",
        name="Rappel court",
        category=SmsTemplateCategory.FOLLOW_UP,
        body="{salutation}, le site envoyé par email est toujours en ligne : {lien_demo} {signature}",
    ),
    "assistant-24-7": SmsTemplate(
        key="assistant-24-7",
        name="Réceptionniste",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body="{salutation}, votre réceptionniste répond à vos clients : {lien_assistant} {signature}",
    ),
}
# Rendered with the « direct » fixture, a slug of this length bills one French segment and two Swiss ones.
_SLUG_ON_THE_MENTION_EDGE = "garage-de-la-grande-place-de-charleville-mezieres"
_TWO_SEGMENT_SLUG = "garage-de-la-grande-place-et-des-environs-de-charleville-mezieres-et-alentours-sud-ouest-nord"
_THREE_SEGMENT_SLUG = "garage-" * 32
# Two segments with a plain « Bonjour », three once a long first name is added to the greeting.
_LONGEST_TWO_SEGMENT_SLUG = "garage-" * 25 + "martin"


class PricelessSmsProvider(AcceptingSmsProvider):
    """An accepting provider whose response carries no price, as smsmode answers our account."""

    async def send(self, *, to_e164: str, sender: str, text: str, **options: Any) -> SmsSendResult:
        result = await super().send(to_e164=to_e164, sender=sender, text=text, **options)
        result.price_cents = None
        return result


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> AcceptingSmsProvider:
    """An accepting SMS provider, an open legal window everywhere, a silent notification and the fixture templates."""
    monkeypatch.setattr(SmsService, "legal_window_refusal", lambda self, country=None: None)
    monkeypatch.setattr(sms_module.notification_service, "notify_sms_event", AsyncCallRecorder())
    monkeypatch.setattr(sms_module, "find_sms_template", _FIXTURE_TEMPLATES.get)
    return AcceptingSmsProvider()


@pytest.fixture
def notifications(monkeypatch: pytest.MonkeyPatch) -> AsyncCallRecorder:
    """The notifications the sends raise, with their detail."""
    recorder = AsyncCallRecorder()
    monkeypatch.setattr(sms_module.notification_service, "notify_sms_event", recorder)
    return recorder


def _prospect(
    db: Session, *, country: str = "FR", phone: str = "06 11 22 33 44", user_id: int = _USER_ID
) -> ProspectDB:
    prospect = ProspectDB(
        name="Garage Martin",
        category="Garage automobile",
        phone=phone,
        country=country,
        source="google",
        confidence=2,
        user_id=user_id,
    )
    db.add(prospect)
    db.commit()
    return prospect


def _config(db: Session, sender: str = "Dibodev") -> SmsConfig:
    config = db.query(SmsConfig).filter(SmsConfig.user_id == _USER_ID).first()
    if config is None:
        config = SmsConfig(user_id=_USER_ID, sender=sender)
        db.add(config)
        db.commit()
    return config


def _send(
    db: Session,
    provider: AcceptingSmsProvider,
    prospect: ProspectDB,
    *,
    demo_url: str = "https://demo.dibodev.fr/s/garage-martin",
    cold: bool = True,
) -> sms_module.SmsSendOutcome:
    return asyncio.run(
        SmsService(provider=provider).send_to_prospect(
            db, user_id=_USER_ID, prospect=prospect, config=_config(db), demo_url=demo_url, cold=cold
        )
    )


def _with_salutation(monkeypatch: pytest.MonkeyPatch, salutation: str) -> None:
    """Make every rendered SMS greet with *salutation* (a resolved decision maker)."""
    original_build = SmsVariables.build_for_prospect

    def build_with_salutation(db: Session, **kwargs: Any) -> dict[str, str]:
        return {**original_build(db, **kwargs), SmsVariables.SALUTATION: salutation}

    monkeypatch.setattr(SmsVariables, "build_for_prospect", build_with_salutation)


class TestSegmentBudget:
    def test_a_message_over_two_segments_is_refused_and_never_sent(
        self, db: Session, provider: AcceptingSmsProvider
    ) -> None:
        outcome = _send(db, provider, _prospect(db), demo_url=f"https://demo.dibodev.fr/s/{_THREE_SEGMENT_SLUG}")

        assert not outcome.sent
        assert outcome.reason is not None and "trop long" in outcome.reason and "la limite est de 2" in outcome.reason
        assert len(outcome.reason) <= 160  # the campaign queue keeps 160 characters of it
        assert provider.texts == []
        assert db.query(SmsMessage).count() == 0

    def test_a_two_segment_message_is_sent(self, db: Session, provider: AcceptingSmsProvider) -> None:
        outcome = _send(db, provider, _prospect(db), demo_url=f"https://demo.dibodev.fr/s/{_TWO_SEGMENT_SLUG}")

        assert outcome.sent
        assert outcome.message is not None and outcome.message.segments == 2

    def test_a_one_segment_message_is_sent_without_any_mention_of_ours(
        self, db: Session, provider: AcceptingSmsProvider
    ) -> None:
        outcome = _send(db, provider, _prospect(db))

        assert outcome.sent
        [text] = provider.texts
        assert text == (
            "Bonjour, j'ai préparé un site pour Garage Martin, il est déjà en ligne : demo.dibodev.fr/s/garage-martin"
        )
        assert "STOP" not in text and "36180" not in text
        assert outcome.message is not None and outcome.message.segments == 1

    def test_the_mention_reserve_of_the_destination_decides_the_segment_count(
        self, db: Session, provider: AcceptingSmsProvider
    ) -> None:
        """The same body bills one French segment (14 characters reserved) and two Swiss ones (25 reserved)."""
        demo_url = f"https://demo.dibodev.fr/s/{_SLUG_ON_THE_MENTION_EDGE}"
        french = _send(db, provider, _prospect(db), demo_url=demo_url)
        swiss = _send(db, provider, _prospect(db, country="CH", phone="079 123 45 67"), demo_url=demo_url)

        assert french.sent and swiss.sent
        assert provider.texts[0] == provider.texts[1]
        assert french.message is not None and french.message.segments == 1
        assert swiss.message is not None and swiss.message.segments == 2

    def test_the_first_name_stays_while_the_message_fits_two_segments(
        self, db: Session, provider: AcceptingSmsProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _with_salutation(monkeypatch, "Bonjour Jean-Christophe")

        outcome = _send(db, provider, _prospect(db), demo_url=f"https://demo.dibodev.fr/s/{_TWO_SEGMENT_SLUG}")

        assert outcome.sent
        assert provider.texts[0].startswith("Bonjour Jean-Christophe, ")

    def test_the_first_name_is_dropped_only_beyond_two_segments(
        self, db: Session, provider: AcceptingSmsProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _with_salutation(monkeypatch, "Bonjour Marie-Christine-Alexandra-Gwendoline")

        outcome = _send(db, provider, _prospect(db), demo_url=f"https://demo.dibodev.fr/s/{_LONGEST_TWO_SEGMENT_SLUG}")

        assert outcome.sent
        assert provider.texts[0].startswith("Bonjour, j'ai préparé")
        assert outcome.message is not None and outcome.message.segments == 2


class TestCountryGuard:
    def test_a_belgian_prospect_is_refused_with_the_reason(self, db: Session, provider: AcceptingSmsProvider) -> None:
        outcome = _send(db, provider, _prospect(db, country="BE", phone="0470 12 34 56"))

        assert (outcome.sent, outcome.reason) == (False, "Pas de SMS de prospection vers ce pays (Belgique)")
        assert provider.texts == []

    def test_a_canadian_prospect_is_refused_although_the_default_profile_is_france(
        self, db: Session, provider: AcceptingSmsProvider
    ) -> None:
        outcome = _send(db, provider, _prospect(db, country="CA", phone="+1 514 555 0199"))

        assert (outcome.sent, outcome.reason) == (False, "Pas de SMS de prospection vers ce pays (Canada (Québec))")

    def test_an_unknown_country_is_refused(self, db: Session, provider: AcceptingSmsProvider) -> None:
        outcome = _send(db, provider, _prospect(db, country="XX"))

        assert (outcome.sent, outcome.reason) == (False, "Pays « XX » inconnu : pas de SMS de prospection")

    def test_a_swiss_079_without_country_code_reaches_a_swiss_mobile(
        self, db: Session, provider: AcceptingSmsProvider
    ) -> None:
        outcome = _send(db, provider, _prospect(db, country="CH", phone="079 123 45 67"))

        assert outcome.sent
        assert provider.sends[0]["to_e164"] == "+41791234567"
        assert outcome.message is not None and outcome.message.to_e164 == "+41791234567"

    def test_the_same_079_stays_a_french_mobile_for_a_french_prospect(
        self, db: Session, provider: AcceptingSmsProvider
    ) -> None:
        outcome = _send(db, provider, _prospect(db, country="FR", phone="079 123 45 67"))

        assert outcome.sent
        assert provider.sends[0]["to_e164"] == "+33791234567"

    def test_a_swiss_prospect_with_only_a_landline_has_no_mobile(
        self, db: Session, provider: AcceptingSmsProvider
    ) -> None:
        outcome = _send(db, provider, _prospect(db, country="CH", phone="022 123 45 67"))

        assert (outcome.sent, outcome.reason) == (
            False,
            "Pas de mobile pour ce prospect dans la numérotation de son pays",
        )

    def test_the_window_is_read_in_the_prospect_country(self, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
        """July 14th is a working Tuesday in Zurich and a holiday in Paris."""
        monkeypatch.setattr(SmsSendWindow, "now", lambda self: datetime(2026, 7, 14, 10, 0))
        monkeypatch.setattr(sms_module.notification_service, "notify_sms_event", AsyncCallRecorder())
        monkeypatch.setattr(sms_module.activity_log_service, "record", lambda **_: None)
        monkeypatch.setattr(sms_module, "find_sms_template", _FIXTURE_TEMPLATES.get)
        provider = AcceptingSmsProvider()

        swiss = _send(db, provider, _prospect(db, country="CH", phone="079 123 45 67"))
        french = _send(db, provider, _prospect(db))

        assert swiss.sent
        assert not french.sent and french.reason is not None and "fenêtre légale" in french.reason


class TestOptOutMention:
    def test_a_prospecting_sms_asks_smsmode_for_its_mention(self, db: Session, provider: AcceptingSmsProvider) -> None:
        outcome = _send(db, provider, _prospect(db))

        assert outcome.sent
        assert provider.sends[0]["opt_out_mention"] is True

    def test_a_manual_sms_asks_for_the_mention_too(self, db: Session, provider: AcceptingSmsProvider) -> None:
        outcome = asyncio.run(
            SmsService(provider=provider).send_manual(
                db, user_id=_USER_ID, config=_config(db), to_raw="06 11 22 33 44", text="Bonjour, un essai"
            )
        )

        assert outcome.sent
        assert provider.sends[0]["opt_out_mention"] is True
        assert provider.texts[0] == "Bonjour, un essai"
        assert outcome.message is not None and outcome.message.kind == SmsMessageKind.PROSPECTING.value

    def test_a_service_sms_carries_no_mention(self, db: Session, provider: AcceptingSmsProvider) -> None:
        outcome = asyncio.run(
            SmsService(provider=provider).send_service_message(
                db,
                user_id=_USER_ID,
                config=_config(db),
                to_e164="+33611223344",
                text="Nouvelle demande",
                recipient_name="G",
            )
        )

        assert outcome.sent
        assert provider.sends[0]["opt_out_mention"] is False
        assert provider.texts[0] == "Nouvelle demande"

    def test_what_smsmode_acknowledges_wins_over_our_count(self, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(SmsService, "legal_window_refusal", lambda self, country=None: None)
        monkeypatch.setattr(sms_module.notification_service, "notify_sms_event", AsyncCallRecorder())
        monkeypatch.setattr(sms_module, "find_sms_template", _FIXTURE_TEMPLATES.get)
        provider = AcceptingSmsProvider(provider_segments=2, provider_text="Bonjour… STOP 36034")

        outcome = _send(db, provider, _prospect(db))

        assert outcome.sent
        assert outcome.message is not None and outcome.message.segments == 2
        assert (outcome.provider_segments, outcome.provider_text) == (2, "Bonjour… STOP 36034")


class TestCostByCountry:
    def test_a_swiss_send_is_priced_at_the_swiss_rate_when_smsmode_gives_none(
        self, db: Session, notifications: AsyncCallRecorder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(SmsService, "legal_window_refusal", lambda self, country=None: None)
        monkeypatch.setattr(sms_module, "find_sms_template", _FIXTURE_TEMPLATES.get)
        monkeypatch.setattr(settings, "smsmode_price_per_segment_eur", 0.061)

        outcome = _send(
            db,
            PricelessSmsProvider(),
            _prospect(db, country="CH", phone="079 123 45 67"),
            demo_url=f"https://demo.dibodev.fr/s/{_TWO_SEGMENT_SLUG}",
        )

        assert outcome.sent
        assert outcome.message is not None
        assert (outcome.message.segments, outcome.message.price_cents) == (2, 13)
        assert notifications.calls[-1]["detail"] == "2 SMS · ≈ 13 c"

    def test_a_french_send_is_priced_at_the_account_french_rate(
        self, db: Session, notifications: AsyncCallRecorder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(SmsService, "legal_window_refusal", lambda self, country=None: None)
        monkeypatch.setattr(sms_module, "find_sms_template", _FIXTURE_TEMPLATES.get)
        monkeypatch.setattr(settings, "smsmode_price_per_segment_eur", 0.061)

        outcome = _send(db, PricelessSmsProvider(), _prospect(db))

        assert outcome.sent
        assert outcome.message is not None and outcome.message.price_cents == 6
        assert notifications.calls[-1]["detail"] == "1 SMS · ≈ 6 c"


class TestTouchesFromHistory:
    def test_a_second_campaign_sms_is_the_relance_and_a_third_is_refused(
        self, db: Session, provider: AcceptingSmsProvider
    ) -> None:
        """The wave 4 SMS arm: a first campaign on day 1, a second one three days later, nothing after."""
        prospect = _prospect(db)

        first = _send(db, provider, prospect, cold=True)
        relance = _send(db, provider, prospect, cold=True)
        third = _send(db, provider, prospect, cold=True)

        assert first.sent and first.message is not None
        assert first.message.kind == SmsMessageKind.FIRST_CONTACT.value
        assert relance.sent and relance.message is not None
        assert relance.message.kind == SmsMessageKind.FOLLOW_UP.value
        assert (third.sent, third.reason) == (False, SmsProspectingRules.SEQUENCE_COMPLETE)
        assert len(provider.texts) == 2

    def test_a_relance_follows_a_first_contact_sms(self, db: Session, provider: AcceptingSmsProvider) -> None:
        prospect = _prospect(db)
        _send(db, provider, prospect, cold=True)

        relance = _send(db, provider, prospect, cold=False)

        assert relance.sent and relance.message is not None
        assert relance.message.kind == SmsMessageKind.FOLLOW_UP.value
        assert "le site envoyé par email" in provider.texts[1]

    def test_a_relance_without_any_first_contact_is_refused(self, db: Session, provider: AcceptingSmsProvider) -> None:
        outcome = _send(db, provider, _prospect(db), cold=False)

        assert (outcome.sent, outcome.reason) == (False, SmsProspectingRules.NO_FIRST_CONTACT_BEFORE_FOLLOW_UP)
        assert provider.texts == []

    def test_an_emailed_prospect_gets_one_sms_its_relance(self, db: Session, provider: AcceptingSmsProvider) -> None:
        prospect = _prospect(db)
        db.add(
            EmailLog(
                user_id=_USER_ID,
                prospect_id=prospect.id,
                recipient_email="garage@example.com",
                subject="Votre site",
                body_html="<p>Bonjour</p>",
                provider="resend",
                status="sent",
                sent_at=datetime(2026, 9, 1, 9, 0),
            )
        )
        db.commit()

        relance = _send(db, provider, prospect, cold=False)
        second = _send(db, provider, prospect, cold=True)

        assert relance.sent and relance.message is not None
        assert relance.message.kind == SmsMessageKind.FOLLOW_UP.value
        assert (second.sent, second.reason) == (False, SmsProspectingRules.SEQUENCE_COMPLETE)


class TestContactPhoneGuard:
    """A template giving the sender's phone (``{telephone}``) never leaves with the phone unset."""

    _TEMPLATE = SmsTemplate(
        key="fixture-telephone",
        name="Fixture téléphone",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body="{salutation}, votre site est en ligne : {lien_demo} Un mot me suffit au {telephone}. {signature}",
    )

    def test_the_guard_reads_the_rendered_variable(self) -> None:
        assert SmsService.contact_phone_refusal(self._TEMPLATE, {}) == (
            "Renseignez votre téléphone de contact dans votre profil"
        )
        assert SmsService.contact_phone_refusal(self._TEMPLATE, {"telephone": "  "}) is not None
        assert SmsService.contact_phone_refusal(self._TEMPLATE, {"telephone": "06 11 22 33 44"}) is None
        assert SmsService.contact_phone_refusal(_FIXTURE_TEMPLATES["direct"], {}) is None

    def test_a_send_without_a_contact_phone_is_refused(
        self, db: Session, provider: AcceptingSmsProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sms_module, "find_sms_template", lambda key: self._TEMPLATE)

        outcome = _send(db, provider, _prospect(db))

        assert (outcome.sent, outcome.reason) == (False, "Renseignez votre téléphone de contact dans votre profil")
        assert provider.texts == []

    def test_a_send_with_the_phone_resolved_leaves(
        self, db: Session, provider: AcceptingSmsProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sms_module, "find_sms_template", lambda key: self._TEMPLATE)
        original_build = SmsVariables.build_for_prospect

        def build_with_phone(db: Session, **kwargs: Any) -> dict[str, str]:
            return {**original_build(db, **kwargs), "telephone": "06 11 22 33 44"}

        monkeypatch.setattr(SmsVariables, "build_for_prospect", build_with_phone)

        outcome = _send(db, provider, _prospect(db))

        assert outcome.sent
        assert "au 06 11 22 33 44" in provider.texts[0]


class TestManualComposer:
    @pytest.mark.parametrize(
        ("sender", "text", "reason"),
        [
            ("", "Nouvelle demande", "Renseignez un nom d'expéditeur dans Paramètres → Relance SMS"),
            ("Dibodev", "a" * 320, "Message trop long : il partirait en 3 SMS. Raccourcissez-le pour tenir en 2."),
        ],
    )
    def test_a_missing_sender_and_a_third_segment_are_refused(
        self, db: Session, provider: AcceptingSmsProvider, sender: str, text: str, reason: str
    ) -> None:
        outcome = asyncio.run(
            SmsService(provider=provider).send_manual(
                db, user_id=_USER_ID, config=_config(db, sender=sender), to_raw="06 11 22 33 44", text=text
            )
        )

        assert (outcome.sent, outcome.reason) == (False, reason)
        assert provider.texts == []

    def test_a_saved_swiss_prospect_number_is_read_in_his_country(
        self, db: Session, provider: AcceptingSmsProvider
    ) -> None:
        prospect = _prospect(db, country="CH", phone="079 123 45 67")

        outcome = asyncio.run(
            SmsService(provider=provider).send_manual(
                db,
                user_id=_USER_ID,
                config=_config(db),
                to_raw="079 123 45 67",
                text="Bonjour",
                prospect_id=prospect.id,
            )
        )

        assert outcome.sent
        assert provider.sends[0]["to_e164"] == "+41791234567"

    def test_a_saved_belgian_prospect_is_refused_by_the_country_guard(
        self, db: Session, provider: AcceptingSmsProvider
    ) -> None:
        prospect = _prospect(db, country="BE", phone="0470 12 34 56")

        outcome = asyncio.run(
            SmsService(provider=provider).send_manual(
                db,
                user_id=_USER_ID,
                config=_config(db),
                to_raw="0470 12 34 56",
                text="Bonjour",
                prospect_id=prospect.id,
            )
        )

        assert (outcome.sent, outcome.reason) == (False, "Pas de SMS de prospection vers ce pays (Belgique)")
        assert provider.texts == []

    def test_a_number_of_another_country_is_refused_for_a_saved_prospect(
        self, db: Session, provider: AcceptingSmsProvider
    ) -> None:
        prospect = _prospect(db, country="CH", phone="079 123 45 67")

        outcome = asyncio.run(
            SmsService(provider=provider).send_manual(
                db,
                user_id=_USER_ID,
                config=_config(db),
                to_raw="06 11 22 33 44",
                text="Bonjour",
                prospect_id=prospect.id,
            )
        )

        assert (outcome.sent, outcome.reason) == (
            False,
            "Numéro invalide : un mobile du pays du prospect (Suisse) est requis",
        )

    def test_a_bare_number_must_stay_a_french_mobile(self, db: Session, provider: AcceptingSmsProvider) -> None:
        outcome = asyncio.run(
            SmsService(provider=provider).send_manual(
                db, user_id=_USER_ID, config=_config(db), to_raw="+41 79 123 45 67", text="Bonjour"
            )
        )

        assert (outcome.sent, outcome.reason) == (False, "Numéro invalide : un mobile français 06/07 est requis")

    def test_another_user_prospect_is_refused(self, db: Session, provider: AcceptingSmsProvider) -> None:
        stranger = _prospect(db, user_id=99)

        outcome = asyncio.run(
            SmsService(provider=provider).send_manual(
                db,
                user_id=_USER_ID,
                config=_config(db),
                to_raw="06 11 22 33 44",
                text="Bonjour",
                prospect_id=stranger.id,
            )
        )

        assert (outcome.sent, outcome.reason) == (False, "Prospect introuvable")
        assert provider.texts == []
        assert stranger.contacted is False


@pytest.mark.parametrize(
    ("sender", "text", "reason"),
    [
        ("", "Nouvelle demande", "Renseignez un nom d'expéditeur dans Paramètres → Relance SMS"),
        ("Dibodev", "a" * 161, "Message trop long : il partirait en 2 SMS. Raccourcissez-le pour tenir en 1 seul."),
        ("Dibodev", "   ", "Message vide"),
    ],
)
def test_the_service_sms_refuses_a_missing_sender_a_second_segment_and_an_empty_body(
    db: Session, provider: AcceptingSmsProvider, sender: str, text: str, reason: str
) -> None:
    outcome = asyncio.run(
        SmsService(provider=provider).send_service_message(
            db,
            user_id=_USER_ID,
            config=_config(db, sender=sender),
            to_e164="+33611223344",
            text=text,
            recipient_name="G",
        )
    )

    assert (outcome.sent, outcome.reason) == (False, reason)
    assert provider.texts == []


def test_a_receptionist_sms_looks_its_assistant_up_once(
    db: Session, provider: AcceptingSmsProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The template's fallback, the guard, the link and the countdown all read the same lookup."""
    prospect = _prospect(db)
    assistant = ai_assistant_service.create(
        db,
        user_id=_USER_ID,
        business_name="Garage Martin",
        prospect_id=prospect.id,
        country="FR",
        use_brand_color=False,
    )
    lookups: list[tuple[int, int]] = []

    def counting_lookup(db: Session, *, prospect_id: int, user_id: int) -> AiAssistant | None:
        lookups.append((prospect_id, user_id))
        return assistant

    monkeypatch.setattr(ai_assistant_service, "get_active_for_prospect", counting_lookup)

    outcome = asyncio.run(
        SmsService(provider=provider).send_to_prospect(
            db,
            user_id=_USER_ID,
            prospect=prospect,
            config=_config(db),
            demo_url="",
            cold=True,
            template_key="assistant-24-7",
        )
    )

    assert outcome.sent
    assert lookups == [(prospect.id, _USER_ID)]
    assert provider.texts[0].endswith("/s/ia/garage-martin")
    assert assistant.demo_link_sent_at is not None
