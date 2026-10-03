"""Email and SMS renderers write the body in the country the prospect's substitution map carries."""

from __future__ import annotations

from services.email_sending_service import EmailSendingService
from services.regional_lexicon import RegionalLexicon
from services.sms.templates import render_sms_template


def _map(country: str | None) -> dict[str, str]:
    variables = {"entreprise": "Paysagement Tremblay", "lien_demo": "demo.dibodev.fr/tremblay"}
    if country is not None:
        variables[RegionalLexicon.COUNTRY_KEY] = country
    return variables


def test_an_email_template_keeps_its_french_elsewhere_and_never_shows_the_country() -> None:
    template = "{entreprise} : votre devis par e-mail"
    assert EmailSendingService(None).replace_variables(template, _map("FR")) == (
        "Paysagement Tremblay : votre devis par e-mail"
    )
    assert EmailSendingService(None).replace_variables(template, _map(None)) == (
        "Paysagement Tremblay : votre devis par e-mail"
    )
    assert "CA" not in EmailSendingService(None).replace_variables("{entreprise}", _map("CA"))


def test_an_sms_template_keeps_its_french_elsewhere() -> None:
    rendered = render_sms_template("Bonjour, votre devis : {lien_demo}", _map("CH"))
    assert rendered == "Bonjour, votre devis : demo.dibodev.fr/tremblay"
