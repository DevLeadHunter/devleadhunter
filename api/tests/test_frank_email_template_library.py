"""Every email and SMS template is frank: who writes, what was prepared, the price, the withdrawal day, how to say no.

Locks the copy rules of the frank library (``seeders/email_template_seeder.py`` and
``services/sms/templates.py``) so a future edit cannot quietly bring back a vague message:
plain words, no long dash, no « voici / cliquez / ici », a nude ending, a single door, the
price through a variable, and for the receptionist the plain mention of an AI, in the gender of its
first name. The loyalty-card templates have their own rules in ``test_loyalty_card_templates.py``.
"""

from __future__ import annotations

import re

from enums.email_template_category import EmailTemplateCategory
from enums.sms_template_category import SmsTemplateCategory
from seeders.email_template_seeder import EMAIL_TEMPLATE_LIBRARY
from services.sms.templates import (
    DEFAULT_FIRST_CONTACT_KEY,
    DEFAULT_FOLLOW_UP_KEY,
    SMS_TEMPLATE_LIBRARY,
    SmsTemplate,
    find_sms_template,
)

_FORBIDDEN_WORDS = re.compile(r"\b(voici|cliquez|ici)\b", re.IGNORECASE)
_LONG_DASHES = ("—", "–")
_BIG_BRANDS = ("google", "apple", "facebook", "instagram")
_EXIT_MARKERS = ("non", "rien à faire")
_CLOSING_MARKERS = (*_EXIT_MARKERS, "Prenez votre temps")
_SINGLE_DOOR_RECEPTIONIST_EMAILS = ("Réceptionniste IA - franc", "Réceptionniste IA - en bref")
_GENDERED_RECEPTIONIST_WORDS = re.compile(
    r"\b(il|elle|virtuel|virtuelle|préparée|une réceptionniste|un réceptionniste|la réceptionniste)\b", re.IGNORECASE
)
_VARIABLE = re.compile(r"\{[a-z_]+\}")
_MODULE_EMAIL_NAME_PREFIXES = ("Réceptionniste", "Carte fidélité")
_MODULE_SMS_KEY_PREFIXES = ("assistant-", "carte-")
_SMS_DOOR_VARIABLES = ("lien_demo", "lien_video", "lien_assistant", "lien_video_assistant", "lien_carte")
_PRICE_VARIABLES = ("prix", "prix_assistant", "prix_carte")


def _website_emails() -> list[dict[str, object]]:
    return [
        template
        for template in EMAIL_TEMPLATE_LIBRARY
        if not str(template["name"]).startswith(_MODULE_EMAIL_NAME_PREFIXES)
    ]


def _receptionist_emails() -> list[dict[str, object]]:
    return [template for template in EMAIL_TEMPLATE_LIBRARY if str(template["name"]).startswith("Réceptionniste")]


def _receptionist_sms() -> list[SmsTemplate]:
    return [template for template in SMS_TEMPLATE_LIBRARY if template.key.startswith("assistant-")]


def _website_sms() -> list[SmsTemplate]:
    return [template for template in SMS_TEMPLATE_LIBRARY if not template.key.startswith(_MODULE_SMS_KEY_PREFIXES)]


class TestEmailLibraryShape:
    def test_names_are_unique(self) -> None:
        names = [str(template["name"]) for template in EMAIL_TEMPLATE_LIBRARY]
        assert len(names) == len(set(names))

    def test_the_frank_templates_are_pinned_first(self) -> None:
        by_name = {str(template["name"]): template for template in EMAIL_TEMPLATE_LIBRARY}
        first_emails = [t for t in EMAIL_TEMPLATE_LIBRARY if t["category"] == EmailTemplateCategory.FIRST_EMAIL.value]
        follow_ups = [t for t in EMAIL_TEMPLATE_LIBRARY if t["category"] == EmailTemplateCategory.FOLLOW_UP.value]
        assert by_name["Franc - premier contact"]["sort_order"] == max(int(t["sort_order"]) for t in first_emails)  # type: ignore[call-overload]
        assert by_name["Franc - relance"]["sort_order"] == max(int(t["sort_order"]) for t in follow_ups)  # type: ignore[call-overload]

    def test_the_dropped_angles_are_gone(self) -> None:
        names = {str(template["name"]) for template in EMAIL_TEMPLATE_LIBRARY}
        for dropped in (
            "Bouche-à-oreille - on vous retrouve",
            "Autonomie - vous gardez la main",
            "Urgence douce",
            "Site en panne - relance",
        ):
            assert dropped not in names, dropped
        assert not any(name.startswith("Assistant IA") for name in names)


class TestEmailCopyRules:
    def test_plain_words_everywhere(self) -> None:
        for template in EMAIL_TEMPLATE_LIBRARY:
            copy = f"{template['subject']} {template['body_html']}"
            assert not any(dash in copy for dash in _LONG_DASHES), template["name"]
            assert _FORBIDDEN_WORDS.search(copy) is None, template["name"]
            assert "http" not in copy, template["name"]

    def test_subjects_are_short_lower_case_and_brand_free(self) -> None:
        for template in EMAIL_TEMPLATE_LIBRARY:
            subject = str(template["subject"])
            assert subject[0].islower() or subject.startswith("{"), subject
            assert len(subject) <= 60, subject
            assert not any(brand in subject.lower() for brand in _BIG_BRANDS), subject

    def test_bodies_end_nude_so_the_signature_block_is_not_doubled(self) -> None:
        for template in EMAIL_TEMPLATE_LIBRARY:
            body = str(template["body_html"])
            assert "{signature}" not in body, template["name"]
            assert body.endswith("</p>"), template["name"]
            last_paragraph = body.rsplit("<p>", 1)[1]
            assert any(marker in last_paragraph for marker in _CLOSING_MARKERS), template["name"]

    def test_no_follow_up_promises_to_be_the_last_message_nor_begs_for_a_no(self) -> None:
        for template in EMAIL_TEMPLATE_LIBRARY:
            body = str(template["body_html"])
            assert "Dernier message" not in body and "promis" not in body, template["name"]
            assert "non merci" not in body and "Je range mes démos" not in body, template["name"]

    def test_every_website_email_says_the_price_the_day_and_how_to_say_no(self) -> None:
        for template in _website_emails():
            body = str(template["body_html"])
            assert "{prix}" in body, template["name"]
            assert "{date_expiration}" in body, template["name"]
            assert "{prix_assistant}" not in body and "{prix_carte}" not in body, template["name"]
            assert any(marker in body for marker in _EXIT_MARKERS), template["name"]

    def test_every_website_email_opens_exactly_one_door(self) -> None:
        for template in _website_emails():
            body = str(template["body_html"])
            doors = body.count("{lien_demo}") + body.count("{vignette_video}") + body.count("{lien_carte}")
            assert doors == 1, template["name"]

    def test_the_first_contact_says_who_writes(self) -> None:
        for template in _website_emails():
            if template["category"] != EmailTemplateCategory.FIRST_EMAIL.value:
                continue
            if template["name"] == "Franc - dernier rappel avant retrait":
                continue
            assert "Je fais des sites web" in str(template["body_html"]), template["name"]


class TestReceptionistEmailCopyRules:
    def test_eight_receptionist_emails_named_after_the_product(self) -> None:
        assert len(_receptionist_emails()) == 8
        for template in _receptionist_emails():
            assert str(template["name"]).startswith("Réceptionniste IA - "), template["name"]

    def test_she_is_plainly_an_ai_with_her_own_address_and_a_refundable_first_month(self) -> None:
        for template in _receptionist_emails():
            body = str(template["body_html"])
            assert "{assistant_virtuel}" in body and "IA" in body, template["name"]
            assert "pas une personne" not in body, template["name"]
            assert "{prix_assistant}" in body and "{prix}" not in body and "{prix_carte}" not in body, template["name"]
            assert "satisfait ou remboursé" in body, template["name"]
            assert "{date_expiration}" in body, template["name"]
            assert any(marker in body for marker in _EXIT_MARKERS), template["name"]

    def test_the_gendered_words_come_from_the_variables(self) -> None:
        for template in _receptionist_emails():
            copy = _VARIABLE.sub("", f"{template['subject']} {template['body_html']}")
            assert _GENDERED_RECEPTIONIST_WORDS.search(copy) is None, template["name"]

    def test_she_never_assumes_the_prospect_has_a_website(self) -> None:
        for template in _receptionist_emails():
            body = str(template["body_html"]).lower()
            assert "votre site" not in body, template["name"]
            assert "installé" not in body, template["name"]

    def test_the_demo_is_linked_once_and_the_first_emails_carry_the_video_thumbnail(self) -> None:
        for template in _receptionist_emails():
            body = str(template["body_html"])
            is_video_template = template["name"] == "Réceptionniste IA - en vidéo"
            shows_the_thumbnail = (
                template["category"] == EmailTemplateCategory.FIRST_EMAIL.value
                and template["name"] not in _SINGLE_DOOR_RECEPTIONIST_EMAILS
            )
            assert body.count("{lien_assistant}") == (0 if is_video_template else 1), template["name"]
            assert body.count("{vignette_video_assistant}") == (1 if shows_the_thumbnail else 0), template["name"]
            assert "{lien_carte}" not in body, template["name"]


class TestSmsCopyRules:
    def test_defaults_are_frank_templates(self) -> None:
        first_contact = find_sms_template(DEFAULT_FIRST_CONTACT_KEY)
        follow_up = find_sms_template(DEFAULT_FOLLOW_UP_KEY)
        assert first_contact is not None and first_contact.uses("telephone") and first_contact.uses("prix")
        assert follow_up is not None and follow_up.uses("telephone") and follow_up.uses("prix")

    def test_every_sms_gives_one_price_one_door_and_the_number_to_answer_to(self) -> None:
        for template in SMS_TEMPLATE_LIBRARY:
            doors = sum(template.body.count(f"{{{link}}}") for link in _SMS_DOOR_VARIABLES)
            assert doors == 1, template.key
            assert template.uses("telephone"), template.key
            assert template.uses("signature"), template.key
            prices_used = [price for price in _PRICE_VARIABLES if template.uses(price)]
            assert len(prices_used) == 1, template.key
            assert _FORBIDDEN_WORDS.search(template.body) is None, template.key
            assert "http" not in template.body, template.key

    def test_website_sms_say_who_writes_and_the_one_time_price(self) -> None:
        for template in _website_sms():
            assert template.uses("prix") and not template.uses("prix_assistant"), template.key
            assert not template.uses("prix_carte"), template.key
            if template.category is SmsTemplateCategory.FIRST_CONTACT:
                assert "je fais des sites web" in template.body.lower(), template.key

    def test_receptionist_sms_say_she_is_an_ai_and_the_refundable_month(self) -> None:
        for template in _receptionist_sms():
            assert template.name.startswith("Réceptionniste IA - "), template.key
            assert "{assistant_virtuel} (IA)" in template.body, template.key
            assert _GENDERED_RECEPTIONIST_WORDS.search(_VARIABLE.sub("", template.body)) is None, template.key
            assert template.uses("prix_assistant") and not template.uses("prix"), template.key
            assert not template.uses("prix_carte"), template.key
            assert "satisfait ou remboursé" in template.body, template.key
            assert "site" not in template.body.lower(), template.key
