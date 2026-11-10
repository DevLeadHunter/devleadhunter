"""``{prix}`` is written in the prospect's currency, from his country."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from enums.sms_template_category import SmsTemplateCategory
from services.email_variables import EmailVariables
from services.regional_lexicon import RegionalLexicon
from services.sms.gsm_segments import is_gsm7
from services.sms.templates import SmsTemplate
from services.sms_service import sms_service
from services.sms_variables import SmsVariables


class _FakeDB:
    """Session stand-in: no enrichment row, no user row."""

    def execute(self, *_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(scalar_one_or_none=lambda: None)

    def get(self, *_args: object) -> None:
        return None


def _prospect(country: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=1, name="Paysagement Tremblay", city="Laval", email="info@tremblay.ca", phone="514 555-0199",
        category="paysagiste", website=None, country=country,
    )  # fmt: skip


@pytest.mark.parametrize(
    ("country", "price"),
    [
        ("FR", "500 €"),
        ("CH", "470 CHF"),
        ("CA", "800 $ CA"),
        ("BE", "500 €"),
    ],
)
def test_email_prices_follow_the_prospect_country(country: str, price: str) -> None:
    variables = EmailVariables.build_for_prospect(_FakeDB(), _prospect(country), sale_price_cents=50000, user_id=7)
    assert variables[EmailVariables.PRICE] == price
    assert variables[RegionalLexicon.COUNTRY_KEY] == country


@pytest.mark.parametrize(
    ("country", "rendered_price"),
    [
        ("FR", "500 €"),
        ("CH", "470 CHF"),
        ("CA", "800 $ CA"),
    ],
)
def test_sms_prices_follow_the_prospect_country_in_gsm7(country: str, rendered_price: str) -> None:
    """A converted price reads firm in an SMS too, and stays inside GSM-7."""
    variables = SmsVariables.build_for_prospect(
        _FakeDB(), user_id=7, prospect=_prospect(country), sale_price_cents=50000
    )
    template = SmsTemplate(key="prix", name="Prix", category=SmsTemplateCategory.FIRST_CONTACT, body="{prix}")
    body = sms_service.render_template_body(template, variables)
    assert body == rendered_price
    assert is_gsm7(body)
    assert variables[RegionalLexicon.COUNTRY_KEY] == country


def test_an_unset_price_renders_empty_whatever_the_country() -> None:
    variables = EmailVariables.build_for_prospect(_FakeDB(), _prospect("CA"), user_id=7)
    assert variables[EmailVariables.PRICE] == ""
