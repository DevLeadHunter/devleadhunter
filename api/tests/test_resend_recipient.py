"""The recipient field sent to Resend: an accented domain goes out in its ASCII form."""

from services.resend_service import ResendService


def test_an_accented_domain_is_sent_in_its_ascii_form() -> None:
    assert ResendService.recipient_field("info@rochat-contrôles.ch", None) == "info@xn--rochat-contrles-nsb.ch"
    assert (
        ResendService.recipient_field("info@rochat-contrôles.ch", "Rochat")
        == "Rochat <info@xn--rochat-contrles-nsb.ch>"
    )


def test_a_plain_address_is_sent_as_it_is() -> None:
    assert ResendService.recipient_field("contact@garage-exemple.ch", None) == "contact@garage-exemple.ch"
