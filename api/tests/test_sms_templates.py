"""Unit tests for the SMS template library — integrity, rendering, one-segment budget."""

from enums.sms_template_category import SmsTemplateCategory
from services.sms.gsm_segments import is_gsm7, segment_count
from services.sms.templates import (
    DEFAULT_FIRST_CONTACT_KEY,
    DEFAULT_FOLLOW_UP_KEY,
    SMS_TEMPLATE_LIBRARY,
    find_sms_template,
    list_sms_templates,
    render_sms_template,
    resolve_sms_template,
)
from services.sms_config_service import SmsConfigService
from services.sms_service import sms_service
from services.sms_variables import SmsVariables

# A common case: a first name and an 18-character slug (the link is the heaviest variable).
_TYPICAL_VARIABLES: dict[str, str] = {
    "salutation": "Bonjour Geoffrey",
    "entreprise": "Garage Martin Auto",
    "ville": "Poitiers",
    "metier": "garagiste",
    "lien_demo": "demo.dibodev.fr/s/garage-martin-auto",
    "lien_assistant": "demo.dibodev.fr/ia/garage-martin-auto",
    "lien_video": "demo.dibodev.fr/s/v/garage-martin-auto",
    "ancien_site": "garage-martin.fr",
    "prix": "500 €",
    "prix_assistant": "79 €",
    "signature": "Léo",
}


class TestLibraryIntegrity:
    def test_keys_are_unique(self) -> None:
        keys = [template.key for template in SMS_TEMPLATE_LIBRARY]
        assert len(keys) == len(set(keys))

    def test_default_first_contact_template_exists(self) -> None:
        template = find_sms_template(DEFAULT_FIRST_CONTACT_KEY)
        assert template is not None
        assert template.category is SmsTemplateCategory.FIRST_CONTACT

    def test_category_filter(self) -> None:
        first_contact = list_sms_templates(SmsTemplateCategory.FIRST_CONTACT)
        assert first_contact
        assert all(template.category is SmsTemplateCategory.FIRST_CONTACT for template in first_contact)
        assert len(list_sms_templates()) == len(SMS_TEMPLATE_LIBRARY)

    def test_unknown_key_is_none(self) -> None:
        assert find_sms_template("nope") is None

    def test_no_template_writes_the_stop_mention(self) -> None:
        assert all("36180" not in template.body for template in SMS_TEMPLATE_LIBRARY)

    def test_variables_are_declared_in_order(self) -> None:
        template = find_sms_template("video")
        assert template is not None
        assert template.variables == ["salutation", "entreprise", "lien_video", "signature"]
        assert template.uses("lien_video")
        assert not template.uses("lien_demo")

    def test_every_video_template_declares_a_valid_fallback(self) -> None:
        # A video body with no generated video would render an empty link: unacceptable in a sent SMS.
        for template in SMS_TEMPLATE_LIBRARY:
            if not template.uses("lien_video"):
                continue
            assert template.fallback_key is not None, template.key
            fallback = find_sms_template(template.fallback_key)
            assert fallback is not None, template.key
            assert fallback.category is template.category, template.key
            assert not fallback.uses("lien_video"), template.key


class TestResolveFallback:
    def test_video_template_with_a_ready_video_is_kept(self) -> None:
        template = find_sms_template("offre-a-vie-video")
        assert template is not None
        assert resolve_sms_template(template, video_ready=True) is template

    def test_video_template_without_a_video_falls_back_to_its_demo_sibling(self) -> None:
        template = find_sms_template("offre-a-vie-video")
        assert template is not None
        resolved = resolve_sms_template(template, video_ready=False)
        assert resolved.key == "offre-a-vie"

    def test_demo_link_template_never_falls_back(self) -> None:
        template = find_sms_template("offre-a-vie")
        assert template is not None
        assert resolve_sms_template(template, video_ready=False) is template


class TestRender:
    def test_substitutes_variables(self) -> None:
        rendered = render_sms_template("{salutation}, site pour {entreprise}", _TYPICAL_VARIABLES)
        assert rendered == "Bonjour Geoffrey, site pour Garage Martin Auto"

    def test_unknown_or_empty_variable_leaves_no_double_space(self) -> None:
        assert render_sms_template("Bonjour {inconnu} {signature}", {"signature": ""}) == "Bonjour"

    def test_compose_from_template_is_a_first_contact_with_stop_once(self) -> None:
        template = find_sms_template(DEFAULT_FIRST_CONTACT_KEY)
        assert template is not None
        body = sms_service.compose_from_template(template, _TYPICAL_VARIABLES)
        assert body.endswith("STOP au 36180")
        assert body.count("36180") == 1
        # A first contact must NOT claim a prior email.
        assert "par email" not in body
        assert "Garage Martin Auto" in body
        assert "demo.dibodev.fr/s/garage-martin-auto" in body


class TestOneSegmentBudget:
    def test_every_first_contact_template_fits_one_gsm7_segment(self) -> None:
        for template in list_sms_templates(SmsTemplateCategory.FIRST_CONTACT):
            body = sms_service.compose_from_template(template, _TYPICAL_VARIABLES)
            assert is_gsm7(body), template.key
            assert segment_count(body) == 1, f"{template.key}: {len(body)} chars"


class TestFollowUpLibrary:
    def test_default_follow_up_template_exists(self) -> None:
        template = find_sms_template(DEFAULT_FOLLOW_UP_KEY)
        assert template is not None
        assert template.category is SmsTemplateCategory.FOLLOW_UP

    def test_every_follow_up_recalls_the_email_and_fits_one_segment(self) -> None:
        follow_ups = list_sms_templates(SmsTemplateCategory.FOLLOW_UP)
        assert follow_ups
        for template in follow_ups:
            # A J+30 relance says where it comes from: the email sent a month ago.
            assert "email" in template.body, template.key
            body = sms_service.compose_from_template(template, _TYPICAL_VARIABLES)
            assert is_gsm7(body), template.key
            assert segment_count(body) == 1, f"{template.key}: {len(body)} chars"

    def test_relance_choice_rejects_a_first_contact_or_unknown_key(self) -> None:
        service = SmsConfigService()
        for key in (DEFAULT_FIRST_CONTACT_KEY, "nope"):
            try:
                service.set_automation(
                    None,  # type: ignore[arg-type]
                    1,
                    cold_sms_enabled=False,
                    auto_relance_enabled=False,
                    auto_relance_after_days=30,
                    relance_template_key=key,
                )
            except ValueError:
                continue
            raise AssertionError(f"{key} should have been rejected as a relance template")


class TestSmsVariables:
    def test_as_sms_link_drops_scheme_and_keeps_query(self) -> None:
        assert (
            SmsVariables.as_sms_link("https://demo.dibodev.fr/s/chez-mimon?v=A") == "demo.dibodev.fr/s/chez-mimon?v=A"
        )
        assert SmsVariables.as_sms_link("http://demo.dibodev.fr/x") == "demo.dibodev.fr/x"
        assert SmsVariables.as_sms_link(None) == ""

    def test_signature_is_the_first_name(self) -> None:
        assert SmsVariables.signature_for("Léo Guillaume") == "Léo"
        assert SmsVariables.signature_for(" Marie ") == "Marie"
        assert SmsVariables.signature_for("") == ""
        assert SmsVariables.signature_for(None) == ""


class TestAssistantTemplates:
    """The AI-assistant SMS family links `{lien_assistant}`, not the website demo."""

    _KEYS = ("assistant-24-7", "assistant-langues", "assistant-demandes", "assistant-relance", "assistant-prix-cash")

    def test_assistant_templates_exist_and_link_the_assistant(self) -> None:
        for key in self._KEYS:
            template = find_sms_template(key)
            assert template is not None, key
            assert template.uses("lien_assistant"), key
            assert not template.uses("lien_demo"), key

    def test_assistant_first_contacts_do_not_claim_a_prior_email(self) -> None:
        for key in ("assistant-24-7", "assistant-langues", "assistant-demandes"):
            template = find_sms_template(key)
            assert template is not None and template.category is SmsTemplateCategory.FIRST_CONTACT
            assert "email" not in template.body, key

    def test_assistant_relance_is_a_follow_up_recalling_the_email(self) -> None:
        template = find_sms_template("assistant-relance")
        assert template is not None
        assert template.category is SmsTemplateCategory.FOLLOW_UP
        assert "email" in template.body

    def test_assistant_template_renders_the_assistant_link(self) -> None:
        template = find_sms_template("assistant-24-7")
        assert template is not None
        body = render_sms_template(template.body, _TYPICAL_VARIABLES)
        assert "demo.dibodev.fr/ia/garage-martin-auto" in body
        assert "demo.dibodev.fr/s/" not in body
