"""Regional lexicon: Québec words in a French text, every other country left untouched."""

from __future__ import annotations

from services.regional_lexicon import RegionalLexicon


def test_other_countries_and_empty_text_are_untouched() -> None:
    text = "Un devis gratuit par e-mail, sur votre portable."
    assert RegionalLexicon.localize(text, "FR") == text
    assert RegionalLexicon.localize(text, "CH") == text
    assert RegionalLexicon.localize(text, "BE") == text
    assert RegionalLexicon.localize(text, None) == text
    assert RegionalLexicon.localize(text, "xx") == text
    assert RegionalLexicon.localize("", "CA") == ""
    assert RegionalLexicon.localize(None, "CA") == ""


def test_a_rendered_template_without_a_lexicon_country_is_untouched() -> None:
    text = "Votre devis gratuit par e-mail"
    assert RegionalLexicon.localize_rendered(text, {RegionalLexicon.COUNTRY_KEY: "FR"}) == text
    assert RegionalLexicon.localize_rendered(text, {"entreprise": "Tremblay"}) == text
