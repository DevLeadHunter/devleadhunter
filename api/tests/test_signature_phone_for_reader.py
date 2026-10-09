"""The phone of the email signature reads the way the prospect dials it: national in France, international abroad."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.email_signatures import render_signature_html
from services.regional_lexicon import RegionalLexicon

_ICON = '<img src="https://example.com/phone.png" width="13" height="13" alt="">'
_SIGNATURE = (
    f'<p><a href="tel:+33612345678" style="color:#6f5fe0">{_ICON}06&nbsp;12&nbsp;34&nbsp;56&nbsp;78</a>'
    ' <a href="tel:+33612345678">Appelez-moi</a></p>'
)


class _FakeResult:
    def scalar_one_or_none(self) -> SimpleNamespace:
        return SimpleNamespace(content_html=_SIGNATURE)


class _FakeDB:
    def execute(self, _statement: object) -> _FakeResult:
        return _FakeResult()


def _render_for(country: str | None) -> str:
    variables: dict[str, str] = {"prenom": "Alex"}
    if country is not None:
        variables[RegionalLexicon.COUNTRY_KEY] = country
    return render_signature_html(_FakeDB(), 1, variables, user_id=1)


@pytest.mark.parametrize("country", ["CH", "CA", "BE"])
def test_a_prospect_abroad_reads_the_number_in_international_form(country: str) -> None:
    html = _render_for(country)

    assert (
        f'href="tel:+33612345678" style="color:#6f5fe0">{_ICON}+33&nbsp;6&nbsp;12&nbsp;34&nbsp;56&nbsp;78</a>' in html
    )
    assert "06&nbsp;12" not in html


@pytest.mark.parametrize("country", ["FR", None])
def test_a_french_prospect_keeps_the_number_as_written(country: str | None) -> None:
    assert _SIGNATURE in _render_for(country)


def test_a_phone_link_without_a_number_keeps_its_words() -> None:
    assert '<a href="tel:+33612345678">Appelez-moi</a>' in _render_for("CH")
