"""Email footer per country: Canada (CASL) names the sender with a postal address, the others do not."""

from __future__ import annotations

import pytest

from core.config import settings
from services.unsubscribe_service import unsubscribe_service

_LINK = "https://app.example/api/v1/unsubscribe?email=x&token=t"


def test_france_and_switzerland_keep_the_plain_footer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sender_postal_address", "12 rue de l'Atelier, 35000 Rennes")
    for country in ("FR", "CH", None):
        body = unsubscribe_service.add_unsubscribe_footer("<p>Bonjour</p>", _LINK, country=country, sender_name="Léo")
        assert "Envoyé par" not in body
        assert "Se désabonner" in body
