"""A new email template leaves like the library: in the card with the offer table, and signed.

Covers the ways a template is born in the app: created in the editor, or copied when a user edits a
library template. The library migration has its own case in ``test_reseed_frank_email_template_library``.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from enums.email_template_category import EmailTemplateCategory
from enums.email_template_layout import EmailTemplateLayout
from models.email_signature import EmailSignature
from models.email_template import EmailTemplate
from models.user import User
from schemas.email_template import EmailTemplateCreate, EmailTemplateUpdate
from services import email_template_service

_CARD_TABLE = EmailTemplateLayout.CARD_TABLE.value
_PLAIN = EmailTemplateLayout.PLAIN.value


def _user(db: Session, email: str) -> User:
    user = User(name="Léo", email=email, hashed_password="x")
    db.add(user)
    db.commit()
    return user


def _signature(db: Session, user: User, name: str, *, is_default: bool = False) -> EmailSignature:
    signature = EmailSignature(user_id=user.id, name=name, content_html=f"<p>{name}</p>", is_default=is_default)
    db.add(signature)
    db.commit()
    return signature


def _create(db: Session, user: User, **fields: object) -> EmailTemplate:
    return email_template_service.create_template(
        db, user, EmailTemplateCreate(name="Nouveau", subject="objet", body_html="<p>Texte</p>", **fields)
    )


def test_a_new_template_is_dressed_and_signed_with_the_default_signature(db: Session) -> None:
    user = _user(db, "leo@example.com")
    _signature(db, user, "Ancienne")
    default = _signature(db, user, "Signature Dibodev", is_default=True)

    created = _create(db, user)

    assert created.layout == _CARD_TABLE
    assert created.signature_id == default.id


def test_without_a_flagged_default_the_first_signature_signs_it(db: Session) -> None:
    user = _user(db, "leo@example.com")
    first = _signature(db, user, "Première")
    _signature(db, user, "Deuxième")

    assert _create(db, user).signature_id == first.id


def test_an_explicit_choice_is_kept(db: Session) -> None:
    user = _user(db, "leo@example.com")
    _signature(db, user, "Signature Dibodev", is_default=True)

    unsigned = _create(db, user, signature_id=None, layout=EmailTemplateLayout.PLAIN)

    assert unsigned.signature_id is None
    assert unsigned.layout == _PLAIN


def test_a_user_without_signature_gets_an_unsigned_template(db: Session) -> None:
    user = _user(db, "leo@example.com")

    assert _create(db, user).signature_id is None


def test_a_copy_of_a_library_template_is_signed_by_the_user_who_edits_it(db: Session) -> None:
    owner = _user(db, "plateforme@example.com")
    owner_signature = _signature(db, owner, "Signature de la plateforme", is_default=True)
    library = EmailTemplate(
        user_id=owner.id,
        signature_id=owner_signature.id,
        name="Franc - premier contact",
        subject="le site de {entreprise}",
        body_html="<p>Texte</p>",
        variables="[]",
        category=EmailTemplateCategory.FIRST_EMAIL.value,
        layout=_PLAIN,
        is_library=True,
    )
    db.add(library)
    db.commit()
    editor = _user(db, "artisan@example.com")
    editor_signature = _signature(db, editor, "Signature de l'artisan", is_default=True)

    fork = email_template_service.update_template(db, editor, library.id, EmailTemplateUpdate(name="Ma version"))

    assert fork.id != library.id
    assert fork.signature_id == editor_signature.id
    assert fork.layout == _PLAIN
    db.refresh(library)
    assert library.signature_id == owner_signature.id
