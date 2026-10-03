"""Email footer per country: Canada (CASL) names the sender with the postal address of his profile, the others do not."""

from __future__ import annotations

from models.user import User
from services.unsubscribe_service import POSTAL_ADDRESS_MISSING_REFUSAL, unsubscribe_service

_LINK = "https://app.example/api/v1/unsubscribe?email=x&token=t"
_ADDRESS = "12 rue des Lilas, 35000 Rennes, France"


def _sender(*, company_name: str | None = "Dibodev", postal_address: str | None = _ADDRESS) -> User:
    return User(
        name="Jean Dupont",
        email="jean@example.com",
        hashed_password="x",
        company_name=company_name,
        postal_address=postal_address,
    )


def test_the_line_names_the_company_then_the_person_then_the_address() -> None:
    line = unsubscribe_service.sender_identification_line("CA", _sender())
    assert line == "Envoyé par Dibodev (Jean Dupont), 12 rue des Lilas, 35000 Rennes, France"


def test_without_a_company_the_line_names_the_person() -> None:
    assert unsubscribe_service.sender_identification_line("CA", _sender(company_name=None)) == (
        "Envoyé par Jean Dupont, 12 rue des Lilas, 35000 Rennes, France"
    )
    assert unsubscribe_service.sender_identification_line("CA", _sender(company_name="  ")) == (
        "Envoyé par Jean Dupont, 12 rue des Lilas, 35000 Rennes, France"
    )


def test_a_sole_trader_named_as_his_company_is_named_once() -> None:
    line = unsubscribe_service.sender_identification_line("CA", _sender(company_name="jean dupont"))
    assert line == "Envoyé par jean dupont, 12 rue des Lilas, 35000 Rennes, France"


def test_an_address_typed_on_several_lines_reads_on_one() -> None:
    sender = _sender(postal_address="  12 rue des Lilas,\n35000 Rennes\r\n\nFrance  ")
    assert unsubscribe_service.sender_identification_line("CA", sender) == (
        "Envoyé par Dibodev (Jean Dupont), 12 rue des Lilas, 35000 Rennes, France"
    )


def test_no_line_outside_canada() -> None:
    for country in ("FR", "CH", "BE", "LU", None):
        assert unsubscribe_service.sender_identification_line(country, _sender()) == ""


def test_no_line_without_an_address() -> None:
    for postal_address in (None, "", "  \n "):
        assert unsubscribe_service.sender_identification_line("CA", _sender(postal_address=postal_address)) == ""
    assert unsubscribe_service.sender_identification_line("CA", None) == ""


def test_canada_refuses_a_sender_without_an_address_and_only_canada() -> None:
    assert unsubscribe_service.sender_identification_refusal("CA", _sender(postal_address=None)) == (
        POSTAL_ADDRESS_MISSING_REFUSAL
    )
    assert unsubscribe_service.sender_identification_refusal("CA", None) == POSTAL_ADDRESS_MISSING_REFUSAL
    assert unsubscribe_service.sender_identification_refusal("CA", _sender()) is None
    for country in ("FR", "CH", None):
        assert unsubscribe_service.sender_identification_refusal(country, _sender(postal_address=None)) is None


def test_a_canadian_recipient_reads_the_line_in_the_footer() -> None:
    sender = _sender(postal_address="12 rue de l'Atelier, 35000 Rennes, France")
    body = unsubscribe_service.add_unsubscribe_footer("<p>Bonjour</p>", _LINK, country="CA", sender=sender)
    assert "Envoyé par Dibodev (Jean Dupont), 12 rue de l&#x27;Atelier, 35000 Rennes, France" in body
    assert "Se désabonner" in body
    assert _LINK in body


def test_france_and_switzerland_keep_the_plain_footer() -> None:
    for country in ("FR", "CH", None):
        body = unsubscribe_service.add_unsubscribe_footer("<p>Bonjour</p>", _LINK, country=country, sender=_sender())
        assert "Envoyé par" not in body
        assert "Se désabonner" in body


def test_the_canadian_footer_still_strips_cleanly() -> None:
    original = "<html><body><p>Bonjour</p></body></html>"
    with_footer = unsubscribe_service.add_unsubscribe_footer(original, _LINK, country="CA", sender=_sender())
    assert unsubscribe_service.strip_unsubscribe_footer(with_footer) == original
