"""The dressing of a prospecting email: the card, the button, the offer table and the footer slot.

The layout works on the rendered body, so these tests render the real library templates the way a
send does and check what the prospect receives. The invariant behind every case: the layout may
move a sentence into a table row, it never drops one and never reorders the email.
"""

from __future__ import annotations

import re

import pytest
from sqlalchemy.orm import Session

from enums.email_template_layout import EmailTemplateLayout
from models.email_signature import EmailSignature
from models.user import User
from schemas.email_template import EmailTemplateCreate, EmailTemplateUpdate
from schemas.user import UserUpdate
from seeders.email_template_seeder import EMAIL_TEMPLATE_LIBRARY
from services import email_template_service
from services.email_layout import EmailLayout
from services.email_variables import EmailVariables
from services.unsubscribe_service import unsubscribe_service

_DEMO_URL = "https://demo.example/menuiserie-lefort?src=email"
_ASSISTANT_URL = "https://demo.example/ia/menuiserie-lefort?src=email"
_CARD_URL = "https://demo.example/c/menuiserie-lefort?src=email"
_VIDEO_URL = "https://demo.example/v/menuiserie-lefort?src=email"
_ASSISTANT_VIDEO_URL = "https://demo.example/va/menuiserie-lefort?src=email"
_SIGNATURE = (
    '<div style="margin-top:16px;"><!--StartFragment--><table><tr><td>Léo Guillaume</td></tr></table><br></div>'
)
_CARD_TABLE = EmailTemplateLayout.CARD_TABLE.value
_CARD = EmailTemplateLayout.CARD.value


def _variables() -> dict[str, str]:
    """The substitution map of a send, with the links and thumbnails in the form ``EmailVariables`` builds."""
    return {
        EmailVariables.SALUTATION: "Bonjour",
        EmailVariables.COMPANY: "Menuiserie Lefort",
        EmailVariables.CITY: "Rennes",
        EmailVariables.TRADE: "menuisier",
        EmailVariables.OLD_WEBSITE: "menuiserie-lefort.example",
        EmailVariables.DEMO_LINK: EmailVariables.build_demo_link_html(_DEMO_URL),
        EmailVariables.ASSISTANT_LINK: EmailVariables.build_demo_link_html(_ASSISTANT_URL),
        EmailVariables.CARD_LINK: EmailVariables.build_demo_link_html(_CARD_URL),
        EmailVariables.RECEPTIONIST_FIRST_NAME: "Léa",
        EmailVariables.RECEPTIONIST: "une réceptionniste",
        EmailVariables.VIRTUAL_ASSISTANT: "une assistante virtuelle",
        EmailVariables.VIDEO_LINK: _VIDEO_URL,
        EmailVariables.VIDEO_THUMBNAIL: EmailVariables.build_video_thumbnail_html(
            _VIDEO_URL, "https://cdn.example/t.jpg"
        ),
        EmailVariables.ASSISTANT_VIDEO_LINK: _ASSISTANT_VIDEO_URL,
        EmailVariables.ASSISTANT_VIDEO_THUMBNAIL: EmailVariables.build_video_thumbnail_html(
            _ASSISTANT_VIDEO_URL, "https://cdn.example/ta.jpg", "Votre réceptionniste en vidéo"
        ),
        EmailVariables.PRICE: "500 €",
        EmailVariables.PRICE_ASSISTANT: "29 €",
        EmailVariables.CARD_PRICE: "19 €",
        EmailVariables.EXPIRY_DATE: "2 novembre",
    }


def _rendered(body_html: str, variables: dict[str, str]) -> str:
    for key, value in variables.items():
        body_html = body_html.replace(f"{{{key}}}", value)
    return body_html


def _library_body(name: str) -> str:
    return next(str(template["body_html"]) for template in EMAIL_TEMPLATE_LIBRARY if template["name"] == name)


def _dressed(name: str, layout: str = _CARD_TABLE) -> str:
    variables = _variables()
    return EmailLayout.dress(layout, _rendered(_library_body(name), variables), _SIGNATURE, variables, "#6f5fe0")


def _row_labels(html: str) -> list[str]:
    return re.findall(r'class="em-label"[^>]*>([^<]+)</td>', html)


def _letters(html: str) -> str:
    """The text of a fragment without its tags nor its spaces: what must survive the dressing, in order."""
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", html))


def test_a_plain_template_leaves_as_before() -> None:
    variables = _variables()
    body = _rendered(_library_body("Franc - premier contact"), variables)
    assert EmailLayout.dress(EmailTemplateLayout.PLAIN.value, body, _SIGNATURE, variables) == body + _SIGNATURE
    assert EmailLayout.dress(None, body, _SIGNATURE, variables) == body + _SIGNATURE


def test_the_first_contact_gets_its_button_and_its_three_rows() -> None:
    html = _dressed("Franc - premier contact")
    assert _row_labels(html) == ["Prix", "Date", "Réponse"]
    assert "L'essentiel" in html
    assert html.count(f'href="{_DEMO_URL}"') == 2
    assert ">demo.example/menuiserie-lefort</a>" in html
    assert ">Voir mon site</a>" in html
    assert "background-color:#6f5fe0" in html
    assert f'style="{EmailVariables.LINK_STYLE}"' not in html
    assert "C'est 500 €, une seule fois.<span" in html
    assert unsubscribe_service.FOOTER_SLOT in html


def test_a_row_is_not_emphasised_twice() -> None:
    html = _dressed("Franc - premier contact")
    assert "<strong" not in html.split("L'essentiel", 1)[1].split("</table>", 1)[0]


def test_the_short_reminder_gets_two_rows() -> None:
    assert _row_labels(_dressed("Rappel court")) == ["Prix", "Réponse"]


def test_a_follow_up_without_a_closing_question_gets_price_and_date() -> None:
    assert _row_labels(_dressed("Franc - relance")) == ["Prix", "Date"]


def test_a_price_written_before_the_link_keeps_the_email_as_text() -> None:
    html = _dressed("Réceptionniste IA - le prix, sans détour")
    assert _row_labels(html) == []
    assert '<strong style="font-weight:600;color:#141414;">29 €</strong>' in html
    assert ">Parler à Léa</a>" in html


def test_the_table_starts_after_the_last_demo_link() -> None:
    html = _dressed("Réceptionniste IA - le soir, personne ne répond")
    assert _row_labels(html) == ["Prix", "Date", "Réponse"]
    button_at = html.index(">Parler à Léa</a>")
    thumbnail_at = html.index("<img ")
    table_at = html.index("L'essentiel")
    assert button_at < thumbnail_at < table_at


def test_a_video_email_keeps_its_thumbnail_and_gets_no_button() -> None:
    html = _dressed("Vidéo - je vous montre")
    assert _row_labels(html) == ["Prix", "Date", "Réponse"]
    assert 'width="520"' in html and "max-width:520px" in html
    assert "La vidéo : <a" in html
    assert "border-radius:8px" not in html


def test_a_loyalty_card_email_gets_its_own_button() -> None:
    html = _dressed("Carte fidélité - premier contact franc")
    assert ">Voir ma carte</a>" in html
    assert _row_labels(html)[0] == "Prix"


def test_the_card_layout_keeps_the_text_and_emphasises_price_and_date() -> None:
    html = _dressed("Franc - premier contact", _CARD)
    assert _row_labels(html) == []
    assert '<strong style="font-weight:600;color:#141414;">500 €</strong>' in html
    assert '<strong style="font-weight:600;color:#141414;">2 novembre</strong>' in html
    assert ">Voir mon site</a>" in html


@pytest.mark.parametrize("layout", [_CARD, _CARD_TABLE])
@pytest.mark.parametrize("template", EMAIL_TEMPLATE_LIBRARY, ids=lambda template: str(template["name"]))
def test_no_library_template_loses_a_word(template: dict[str, object], layout: str) -> None:
    variables = _variables()
    body = _rendered(str(template["body_html"]), variables)
    dressed_letters = _letters(EmailLayout.dress(layout, body, "", variables))
    position = 0
    for paragraph in re.findall(r"<(?:p|li)[^>]*>(.*?)</(?:p|li)>", body, re.DOTALL):
        letters = _letters(paragraph)
        found_at = dressed_letters.find(letters, position)
        assert found_at != -1, paragraph
        position = found_at + len(letters)


def test_a_paragraph_between_the_offer_and_the_end_stays_text_in_its_place() -> None:
    variables = _variables()
    body = _rendered(
        "<p>Bonjour,</p><p>Votre site : {lien_demo}</p><p>C'est {prix}, une seule fois.</p>"
        "<p>Je le retire le {date_expiration}.</p><p>Je passe à Rennes jeudi.</p><p>Un mot me suffit.</p>",
        variables,
    )
    html = EmailLayout.dress(_CARD_TABLE, body, "", variables)
    assert _row_labels(html) == ["Prix", "Date"]
    assert html.index("</table>") < html.index("Je passe à Rennes jeudi.") < html.index("Un mot me suffit.")


def test_a_single_offer_paragraph_makes_no_table() -> None:
    variables = _variables()
    body = _rendered("<p>Votre site : {lien_demo}</p><p>C'est {prix}.</p><p>Bien à vous,</p><p>Léo</p>", variables)
    assert _row_labels(EmailLayout.dress(_CARD_TABLE, body, "", variables)) == []


def test_an_email_without_a_link_gets_neither_button_nor_table() -> None:
    variables = _variables()
    body = _rendered("<p>Bonjour,</p><p>C'est {prix}.</p><p>Je le retire le {date_expiration}.</p>", variables)
    html = EmailLayout.dress(_CARD_TABLE, body, "", variables)
    assert _row_labels(html) == []
    assert "border-radius:8px" not in html


def test_a_date_inside_a_longer_number_is_not_the_withdrawal_date() -> None:
    variables = _variables()
    body = _rendered("<p>Votre site : {lien_demo}</p><p>C'est {prix}.</p><p>Je passe le 12 novembre.</p>", variables)
    html = EmailLayout.dress(_CARD_TABLE, body, "", variables)
    assert _row_labels(html) == ["Prix", "Réponse"]
    assert "12 novembre" in html and "<strong" not in html.split("L'essentiel", 1)[1]


def test_a_body_that_is_not_made_of_paragraphs_is_left_as_written() -> None:
    variables = _variables()
    body = _rendered("<div>Bonjour,<br>Votre site : {lien_demo}<br>C'est {prix}.</div>", variables)
    html = EmailLayout.dress(_CARD_TABLE, body, "", variables)
    assert _row_labels(html) == []
    assert "<div>Bonjour,<br>Votre site : <a" in html
    assert 'class="em-card"' in html


def test_a_missing_or_malformed_colour_falls_back_to_ink() -> None:
    variables = _variables()
    body = _rendered(_library_body("Franc - premier contact"), variables)
    for accent_color in (None, "", "violet", "#6f5fe"):
        html = EmailLayout.dress(_CARD_TABLE, body, "", variables, accent_color)
        assert "background-color:#141414;border-radius:8px" in html


def test_a_pasted_signature_loses_its_clipboard_markers_and_trailing_break() -> None:
    html = _dressed("Franc - premier contact")
    assert "StartFragment" not in html
    assert "<td>Léo Guillaume</td></tr></table></div>" in html


def test_the_footer_fills_the_slot_and_can_be_stripped_again() -> None:
    dressed = _dressed("Franc - premier contact")
    with_footer = unsubscribe_service.add_unsubscribe_footer(dressed, "https://app.example/unsubscribe?t=old")
    assert unsubscribe_service.FOOTER_SLOT not in with_footer
    assert with_footer.count("Se désabonner") == 1
    assert with_footer.index('class="em-foot"') < with_footer.index("t=old") < with_footer.index("</body>")
    assert unsubscribe_service.strip_unsubscribe_footer(with_footer) == dressed
    readded = unsubscribe_service.add_unsubscribe_footer(
        unsubscribe_service.strip_unsubscribe_footer(with_footer), "https://app.example/unsubscribe?t=new"
    )
    assert "t=new" in readded and "t=old" not in readded


def test_the_dressed_footer_names_the_sender_for_canada() -> None:
    sender = User(name="Jean Dupont", email="jean@example.com", hashed_password="x", postal_address="12 rue des Lilas")
    with_footer = unsubscribe_service.add_unsubscribe_footer(
        _dressed("Franc - premier contact"), "https://app.example/unsubscribe", country="CA", sender=sender
    )
    assert "Envoyé par Jean Dupont, 12 rue des Lilas<br>" in with_footer


def test_preview_values_turn_examples_into_what_a_send_carries() -> None:
    values = EmailVariables.preview_values(
        {
            EmailVariables.DEMO_LINK: "https://demo.example/le-gourmet",
            EmailVariables.VIDEO_LINK: "https://demo.example/v/le-gourmet",
            EmailVariables.VIDEO_THUMBNAIL: "[vignette cliquable de la vidéo]",
            EmailVariables.PRICE: "500 €",
        }
    )
    assert values[EmailVariables.DEMO_LINK] == EmailVariables.build_demo_link_html("https://demo.example/le-gourmet")
    assert 'href="https://demo.example/v/le-gourmet"' in values[EmailVariables.VIDEO_THUMBNAIL]
    assert EmailVariables.PREVIEW_THUMBNAIL_PATH in values[EmailVariables.VIDEO_THUMBNAIL]
    assert values[EmailVariables.PRICE] == "500 €"


def _user(db: Session) -> User:
    user = User(name="Léo", email="leo@example.com", hashed_password="x", email_accent_color="#6f5fe0")
    db.add(user)
    db.commit()
    return user


def test_a_preview_shows_the_email_as_it_leaves(db: Session) -> None:
    user = _user(db)
    signature = EmailSignature(user_id=user.id, name="Signature", content_html="<p>Léo Guillaume</p>", is_default=True)
    db.add(signature)
    db.commit()
    preview = email_template_service.render_preview(
        db,
        user,
        subject="le site de {entreprise}",
        body_html=_library_body("Franc - premier contact"),
        signature_id=signature.id,
        layout=_CARD_TABLE,
        sample_values={
            EmailVariables.SALUTATION: "Bonjour Jean",
            EmailVariables.COMPANY: "Le Gourmet",
            EmailVariables.DEMO_LINK: "https://demo.example/le-gourmet",
            EmailVariables.PRICE: "500 €",
            EmailVariables.EXPIRY_DATE: "12 octobre",
        },
    )
    assert preview.subject == "le site de Le Gourmet"
    assert _row_labels(preview.body_html) == ["Prix", "Date", "Réponse"]
    assert "Léo Guillaume" in preview.body_html
    assert "background-color:#6f5fe0" in preview.body_html
    assert preview.body_html.count("Se désabonner") == 1
    assert unsubscribe_service.FOOTER_SLOT not in preview.body_html


def test_the_layout_travels_with_a_template(db: Session) -> None:
    user = _user(db)
    created = email_template_service.create_template(
        db,
        user,
        EmailTemplateCreate(name="Franc habillé", subject="objet", body_html="<p>Texte</p>", layout=_CARD_TABLE),
    )
    assert email_template_service.to_response(created).layout == EmailTemplateLayout.CARD_TABLE
    untouched = email_template_service.update_template(db, user, created.id, EmailTemplateUpdate(name="Renommé"))
    assert untouched.layout == _CARD_TABLE
    updated = email_template_service.update_template(db, user, created.id, EmailTemplateUpdate(layout=_CARD))
    assert updated.layout == _CARD
    by_default = email_template_service.create_template(
        db, user, EmailTemplateCreate(name="Simple", subject="objet", body_html="<p>Texte</p>")
    )
    assert by_default.layout == EmailTemplateLayout.PLAIN.value


def test_the_profile_colour_is_a_hexadecimal_colour() -> None:
    assert UserUpdate(email_accent_color="#6F5FE0").email_accent_color == "#6f5fe0"
    assert UserUpdate(email_accent_color="").email_accent_color == ""
    with pytest.raises(ValueError, match="#RRGGBB"):
        UserUpdate(email_accent_color="violet")
