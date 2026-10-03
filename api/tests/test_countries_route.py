"""``GET /api/v1/countries``: the facts the dashboard reads per open country."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.routes.countries import router
from services.country_profiles import CountryProfiles


def _countries() -> list[dict[str, object]]:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    response = TestClient(app).get("/api/v1/countries")
    assert response.status_code == 200
    return response.json()


def test_lists_the_open_countries_france_first() -> None:
    payload = _countries()
    assert [entry["code"] for entry in payload] == [profile.code for profile in CountryProfiles.enabled()]
    assert payload[0] == {
        "code": "FR",
        "label": "France",
        "currency": "EUR",
        "dial_code": "+33",
        "postal_code_pattern": r"\d{5}",
        "postal_code_example": "35000",
        "tax_id_label": "SIREN / SIRET",
        "tax_id_example": "123 456 789",
        "tax_id_required": True,
        "sms_prospecting_open": True,
    }


def test_each_country_names_its_fiscal_identifier() -> None:
    payload = {entry["code"]: entry for entry in _countries()}
    assert payload["CH"]["tax_id_label"] == "IDE (CHE)"
    assert payload["CH"]["tax_id_required"] is False
    assert payload["CH"]["postal_code_pattern"] == r"\d{4}"
    assert payload["BE"]["tax_id_label"] == "Numéro BCE"
