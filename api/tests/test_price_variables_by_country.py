"""``{prix}`` and ``{prix_assistant}`` are written in the prospect's currency, from his country."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import services.email_variables as email_variables_module
import services.sms_variables as sms_variables_module
from enums.sms_template_category import SmsTemplateCategory
from services.email_variables import EmailVariables
from services.regional_lexicon import RegionalLexicon
from services.sms.gsm_segments import is_gsm7
from services.sms.templates import SmsTemplate
from services.sms_service import sms_service
from services.sms_variables import SmsVariables


class _FakeDB:
    """Session stand-in: no enrichment row, no user row, no assistant."""

    def execute(self, *_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(scalar_one_or_none=lambda: None)

    def get(self, *_args: object) -> None:
        return None


def _prospect(country: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=1, name="Paysagement Tremblay", city="Laval", email="info@tremblay.ca", phone="514 555-0199",
        category="paysagiste", website=None, country=country,
    )  # fmt: skip


@pytest.fixture(autouse=True)
def _no_assistant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(email_variables_module.ai_assistant_service, "get_active_for_prospect", lambda *_a, **_k: None)
    monkeypatch.setattr(sms_variables_module.AssistantPricingService, "monthly_price_cents", lambda _db, _uid: 2900)


@pytest.mark.parametrize(
    ("country", "price", "assistant_price"),
    [
        ("FR", "500 €", "29 €"),
        ("CH", "≈ 470 CHF", "≈ 27 CHF"),
        ("CA", "≈ 800 $ CA", "≈ 46 $ CA"),
        ("BE", "500 €", "29 €"),
    ],
)
def test_email_prices_follow_the_prospect_country(country: str, price: str, assistant_price: str) -> None:
    variables = EmailVariables.build_for_prospect(
        _FakeDB(), _prospect(country), sale_price_cents=50000, assistant_monthly_price_cents=2900, user_id=7
    )
    assert variables[EmailVariables.PRICE] == price
    assert variables[EmailVariables.PRICE_ASSISTANT] == assistant_price
    assert variables[RegionalLexicon.COUNTRY_KEY] == country


@pytest.mark.parametrize(
    ("country", "rendered_prices"),
    [("FR", "500 € / 29 €"), ("CH", "env. 470 CHF / env. 27 CHF"), ("CA", "env. 800 $ CA / env. 46 $ CA")],
)
def test_sms_prices_follow_the_prospect_country_in_gsm7(country: str, rendered_prices: str) -> None:
    """« ≈ » is outside GSM-7: the SMS writes « env. » so it keeps its 160-character segments."""
    variables = SmsVariables.build_for_prospect(
        _FakeDB(), user_id=7, prospect=_prospect(country), assistant=None, sale_price_cents=50000
    )
    template = SmsTemplate(
        key="prix", name="Prix", category=SmsTemplateCategory.FIRST_CONTACT, body="{prix} / {prix_assistant}"
    )
    body = sms_service.render_template_body(template, variables)
    assert body == rendered_prices
    assert is_gsm7(body)
    assert variables[RegionalLexicon.COUNTRY_KEY] == country


def test_an_unset_price_renders_empty_whatever_the_country() -> None:
    variables = EmailVariables.build_for_prospect(_FakeDB(), _prospect("CA"), user_id=7)
    assert variables[EmailVariables.PRICE] == ""
    assert variables[EmailVariables.PRICE_ASSISTANT] == ""
