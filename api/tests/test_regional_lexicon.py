"""Regional lexicon: Québec words in a French text, every other country left untouched."""

from __future__ import annotations

from services.regional_lexicon import RegionalLexicon


def _quebec(text: str) -> str:
    return RegionalLexicon.localize(text, "CA")


def test_whole_words_are_swapped_with_their_case() -> None:
    assert _quebec("Un devis gratuit sous 48 h.") == "Une soumission gratuite sous 48 h."
    assert _quebec("Devis gratuit") == "Soumission gratuite"
    assert _quebec("DEVIS GRATUIT") == "SOUMISSION GRATUITE"
    assert _quebec("Votre e-mail et votre portable") == "Votre courriel et votre cellulaire"
    assert _quebec("Par email ou par mail") == "Par courriel ou par courriel"


def test_plurals_are_kept() -> None:
    assert _quebec("Vos e-mails et vos portables") == "Vos courriels et vos cellulaires"
    assert _quebec("Comparez des devis détaillés") == "Comparez des soumissions détaillées"
    assert _quebec("Les devis sont gratuits") == "Les soumissions sont gratuites"


def test_the_determiner_agrees_with_the_new_gender() -> None:
    assert _quebec("Demandez le devis") == "Demandez la soumission"
    assert _quebec("Ce devis est clair") == "Cette soumission est claire"
    assert _quebec("Réponse au devis du client") == "Réponse à la soumission du client"
    assert _quebec("Mon devis") == "Ma soumission"


def test_the_adjectives_around_a_copula_agree_too() -> None:
    assert _quebec("Le devis est-il vraiment gratuit ?") == "La soumission est-elle vraiment gratuite ?"
    assert (
        _quebec("un devis écrit, détaillé et sans engagement") == "une soumission écrite, détaillée et sans engagement"
    )
    assert _quebec("Le devis est très clair") == "La soumission est très claire"


def test_an_elided_article_takes_its_full_form_before_a_consonant() -> None:
    assert _quebec("répondez à cet e-mail") == "répondez à ce courriel"
    assert _quebec("L'e-mail et l'adresse") == "Le courriel et l'adresse"
    assert _quebec("une adresse d'e-mail") == "une adresse de courriel"


def test_words_glued_to_others_are_not_touched() -> None:
    assert _quebec("Écrivez-nous sur Gmail") == "Écrivez-nous sur Gmail"
    assert _quebec("un portable-pro et un devisseur") == "un portable-pro et un devisseur"
    assert _quebec("mailing, Hotmail, emailing") == "mailing, Hotmail, emailing"


def test_urls_emails_tags_and_variables_survive() -> None:
    html = (
        '<a href="https://demo.dibodev.fr/devis-express?mail=1" class="mail-link">votre devis</a>'
        " — contact@devis-express.fr — www.devis.ca — {email} {lien_demo}"
    )
    assert _quebec(html) == (
        '<a href="https://demo.dibodev.fr/devis-express?mail=1" class="mail-link">votre soumission</a>'
        " — contact@devis-express.fr — www.devis.ca — {email} {lien_demo}"
    )
    assert _quebec('<a href="mailto:x@y.fr">mail</a>') == '<a href="mailto:x@y.fr">courriel</a>'


def test_other_countries_and_empty_text_are_untouched() -> None:
    text = "Un devis gratuit par e-mail, sur votre portable."
    assert RegionalLexicon.localize(text, "FR") == text
    assert RegionalLexicon.localize(text, "CH") == text
    assert RegionalLexicon.localize(text, "BE") == text
    assert RegionalLexicon.localize(text, None) == text
    assert RegionalLexicon.localize(text, "xx") == text
    assert RegionalLexicon.localize("", "CA") == ""
    assert RegionalLexicon.localize(None, "CA") == ""


def test_localizing_twice_changes_nothing_more() -> None:
    once = _quebec("Un devis gratuit par e-mail.")
    assert _quebec(once) == once


def test_participles_and_plural_adjectives_agree() -> None:
    assert _quebec("Le devis validé") == "La soumission validée"
    assert _quebec("Le devis est toujours gratuit") == "La soumission est toujours gratuite"
    assert _quebec("Des devis gratuits") == "Des soumissions gratuites"
    assert _quebec("DES DEVIS") == "DES SOUMISSIONS"


def test_the_weekend_becomes_the_fin_de_semaine() -> None:
    assert _quebec("Urgence le week-end et les jours fériés") == "Urgence la fin de semaine et les jours fériés"
    assert _quebec("Ouvert tous les week-ends") == "Ouvert toutes les fins de semaine"
    assert _quebec("Jours fériés et week-ends compris") == "Jours fériés et fins de semaine comprises"
    assert _quebec("Le weekend prochain") == "La fin de semaine prochaine"


def test_takeout_is_written_the_quebec_way() -> None:
    assert _quebec("Sur place ou à emporter") == "Sur place ou pour emporter"
    assert _quebec("VENTE À EMPORTER") == "VENTE POUR EMPORTER"


def test_a_rendered_template_is_localized_in_the_country_its_map_carries() -> None:
    assert RegionalLexicon.localize_rendered("Votre devis gratuit par e-mail", {RegionalLexicon.COUNTRY_KEY: "CA"}) == (
        "Votre soumission gratuite par courriel"
    )


def test_a_rendered_template_without_a_lexicon_country_is_untouched() -> None:
    text = "Votre devis gratuit par e-mail"
    assert RegionalLexicon.localize_rendered(text, {RegionalLexicon.COUNTRY_KEY: "FR"}) == text
    assert RegionalLexicon.localize_rendered(text, {"entreprise": "Tremblay"}) == text


def test_the_trade_words_are_written_the_quebec_way() -> None:
    """Québec test sites still said « Artisan électricien » and « tableau électrique » (8 Oct 2026)."""
    assert _quebec("Artisan électricien") == "Entrepreneur électricien"
    assert _quebec("Un seul artisan pour tout votre extérieur") == "Un seul entrepreneur pour tout votre extérieur"
    assert _quebec("Nos artisans et l'artisan du quartier") == "Nos entrepreneurs et l'entrepreneur du quartier"
    assert _quebec("Remplacement du tableau électrique") == "Remplacement du panneau électrique"
    assert _quebec("Un travail artisanal") == "Un travail artisanal"
