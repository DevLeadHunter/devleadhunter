"""The word written before a template variable follows French: « d'Atelier Dupont », « du Jardin », « au Mans ».

Cases taken from the names of real prospects and from the words the library writes before a variable
(« de {entreprise} », « à {ville} », « que {prenom_receptionniste} »).
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from models.user import User
from services import email_template_service
from services.email_sending_service import EmailSendingService
from services.french_elision import FrenchElision


@pytest.mark.parametrize(
    ("template", "value", "expected"),
    [
        ("le site de {entreprise}", "Atelier Dupont", "le site d'Atelier Dupont"),
        ("celui de {entreprise}", "Électricité Faure", "celui d'Électricité Faure"),
        ("celui de {entreprise}", "IB Jardinage", "celui d'IB Jardinage"),
        ("De {entreprise} à vous", "Ô Goût du Jour", "D'Ô Goût du Jour à vous"),
        ("le site de {entreprise}", "Le Jardin de Kyllian", "le site du Jardin de Kyllian"),
        ("le site de {entreprise}", "Les Jardins Tournaisiens", "le site des Jardins Tournaisiens"),
        ("De {entreprise}", "Le Chill 974", "Du Chill 974"),
    ],
)
def test_de_is_elided_before_a_vowel_and_contracted_with_le_and_les(template: str, value: str, expected: str) -> None:
    assert FrenchElision.apply(template, {"entreprise": value}) == expected


@pytest.mark.parametrize(
    "value",
    [
        "Menuiserie Lefort",
        "La Bonne Frite",
        "L'Oasis",
        "Haut-Plateau Electricité",
        "3D Rénovation",
        "Letang Electricité",
    ],
)
def test_any_other_value_keeps_de_for_the_substitution(value: str) -> None:
    assert FrenchElision.apply("le site de {entreprise}", {"entreprise": value}) == "le site de {entreprise}"


def test_a_and_que_follow_the_same_rules() -> None:
    assert FrenchElision.apply("à {ville}", {"ville": "Le Mans"}) == "au Mans"
    assert FrenchElision.apply("À {ville}", {"ville": "Les Herbiers"}) == "Aux Herbiers"
    assert FrenchElision.apply("à {ville}", {"ville": "Angers"}) == "à {ville}"
    assert FrenchElision.apply("ainsi que {prenom_receptionniste}", {"prenom_receptionniste": "Inès"}) == (
        "ainsi qu'Inès"
    )
    assert FrenchElision.apply("que {prenom_receptionniste}", {"prenom_receptionniste": "Hugo"}) == (
        "que {prenom_receptionniste}"
    )


def test_links_prices_missing_values_and_other_words_are_left_alone() -> None:
    variables: dict[str, object] = {
        "lien_demo": '<a href="https://demo.example/atelier">demo.example/atelier</a>',
        "prix": "500 €",
        "entreprise": "",
        "metier": "électricien",
    }
    text = "voir de {lien_demo}, de {prix}, de {entreprise}, de {inconnue}, pour {metier}, aide {metier}"
    assert FrenchElision.apply(text, variables) == text


def test_a_campaign_send_and_a_preview_render_the_elided_word(db: Session) -> None:
    variables = {"entreprise": "Atelier Dupont", "salutation": "Bonjour"}
    rendered = EmailSendingService(db).replace_variables("{salutation}, le site de {entreprise}", variables)
    assert rendered == "Bonjour, le site d'Atelier Dupont"

    user = User(name="Léo", email="leo@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    preview = email_template_service.render_preview(
        db,
        user,
        subject="le site de {entreprise}",
        body_html="<p>J'ai construit celui de {entreprise}.</p>",
        signature_id=None,
        layout="plain",
        sample_values={"entreprise": "Les Jardins Tournaisiens"},
    )
    assert preview.subject == "le site des Jardins Tournaisiens"
    assert "celui des Jardins Tournaisiens." in preview.body_html
