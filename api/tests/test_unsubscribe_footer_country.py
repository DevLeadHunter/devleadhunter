"""Email footer per country: Canada (CASL) names the sender with a postal address, the others do not."""

from __future__ import annotations

import pytest

from core.config import settings
from services.unsubscribe_service import unsubscribe_service

_LINK = "https://app.example/api/v1/unsubscribe?email=x&token=t"


def test_a_canadian_recipient_reads_the_sender_and_his_postal_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sender_postal_address", "12 rue de l'Atelier, 35000 Rennes, France")
    body = unsubscribe_service.add_unsubscribe_footer("<p>Bonjour</p>", _LINK, country="CA", sender_name="Léo")
    assert "Envoyé par Léo, 12 rue de l&#x27;Atelier, 35000 Rennes, France" in body
    assert "Se désabonner" in body
    assert _LINK in body


def test_an_empty_postal_address_never_breaks_the_send(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sender_postal_address", "")
    body = unsubscribe_service.add_unsubscribe_footer("<p>Bonjour</p>", _LINK, country="CA", sender_name="Léo")
    assert "Envoyé par" not in body
    assert "Se désabonner" in body


def test_france_and_switzerland_keep_the_plain_footer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sender_postal_address", "12 rue de l'Atelier, 35000 Rennes")
    for country in ("FR", "CH", None):
        body = unsubscribe_service.add_unsubscribe_footer("<p>Bonjour</p>", _LINK, country=country, sender_name="Léo")
        assert "Envoyé par" not in body
        assert "Se désabonner" in body


def test_the_canadian_footer_still_strips_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sender_postal_address", "12 rue de l'Atelier, 35000 Rennes")
    original = "<html><body><p>Bonjour</p></body></html>"
    with_footer = unsubscribe_service.add_unsubscribe_footer(original, _LINK, country="CA", sender_name="Léo")
    assert unsubscribe_service.strip_unsubscribe_footer(with_footer) == original
