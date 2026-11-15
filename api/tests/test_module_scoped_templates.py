"""What the dashboard reads to show each module its own templates: a template's module, and what a module writes."""

from __future__ import annotations

from collections.abc import Iterator
from typing import ClassVar

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.v1.routes.product_modules import router
from core.database import get_db
from core.product_modules.campaign_offer import CampaignOffer
from core.product_modules.contract import ProductModule
from core.product_modules.registry import product_module_registry
from enums.sms_template_category import SmsTemplateCategory
from models.email_template import EmailTemplate
from models.user import User
from schemas.email_template import EmailTemplateCreate
from services import email_template_service
from services.auth_service import get_current_active_user
from services.product_module_service import product_module_service
from services.sms.templates import SmsTemplate

_CARD_SMS = SmsTemplate(
    key="carte-premier-contact",
    name="Carte - premier contact",
    category=SmsTemplateCategory.FIRST_CONTACT,
    body="{salutation}, votre carte de fidélité est prête : {lien_carte_test} {signature}",
)


class _CardOffer(CampaignOffer):
    """A loyalty card sold by email and by SMS."""

    module_key: ClassVar[str] = "card-module"
    offer_label: ClassVar[str] = "loyalty card"
    expired_offer_skip_reason: ClassVar[str] = "Carte expirée"
    email_link_variables: ClassVar[tuple[str, ...]] = ("lien_carte_test",)
    email_offer_variables: ClassVar[tuple[str, ...]] = ("lien_carte_test", "prix_carte_test")
    sms_link_variables: ClassVar[tuple[str, ...]] = ("lien_carte_test",)
    sms_offer_variables: ClassVar[tuple[str, ...]] = ("lien_carte_test",)
    missing_offer_skip_reason: ClassVar[str] = "Pas de carte"
    missing_offer_launch_summary: ClassVar[str] = "faute de carte"

    def sms_templates(self) -> list[SmsTemplate]:
        """The card's first-contact SMS."""
        return [_CARD_SMS]


class _EmailOnlyOffer(CampaignOffer):
    """An offer sold by email alone: it adds no SMS template to the library."""

    module_key: ClassVar[str] = "email-only-module"
    offer_label: ClassVar[str] = "email-only offer"
    expired_offer_skip_reason: ClassVar[str] = "Offre expirée"
    email_link_variables: ClassVar[tuple[str, ...]] = ("lien_offre_test",)
    email_offer_variables: ClassVar[tuple[str, ...]] = ("lien_offre_test",)
    missing_offer_skip_reason: ClassVar[str] = "Pas d'offre"
    missing_offer_launch_summary: ClassVar[str] = "faute d'offre"


class _CardModule(ProductModule):
    key: ClassVar[str] = "card-module"
    label: ClassVar[str] = "Cartes"
    enabled_by_default: ClassVar[bool] = True

    def campaign_offer(self) -> CampaignOffer:
        """The loyalty card."""
        return _CardOffer()


class _EmailOnlyModule(ProductModule):
    key: ClassVar[str] = "email-only-module"
    label: ClassVar[str] = "Email seul"
    enabled_by_default: ClassVar[bool] = True

    def campaign_offer(self) -> CampaignOffer:
        """The email-only offer."""
        return _EmailOnlyOffer()


class _WritingItsOwnMessagesModule(ProductModule):
    """A module that writes its messages itself, like site care or the missions: no campaign offer."""

    key: ClassVar[str] = "own-messages-module"
    label: ClassVar[str] = "Messages maison"
    enabled_by_default: ClassVar[bool] = True


@pytest.fixture
def three_modules_installed() -> Iterator[None]:
    product_module_registry.use([_CardModule(), _EmailOnlyModule(), _WritingItsOwnMessagesModule()])
    yield


@pytest.fixture
def user(db: Session) -> User:
    user = User(name="Léo", email="leo@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    return user


def _enabled_modules(db: Session, user: User) -> dict[str, dict[str, object]]:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_active_user] = lambda: user
    response = TestClient(app).get("/api/v1/product-modules")
    assert response.status_code == 200
    return {entry["key"]: entry for entry in response.json()}


def _template(db: Session, user: User, body_html: str, *, subject: str = "Votre entreprise") -> EmailTemplate:
    return email_template_service.create_template(
        db, user, EmailTemplateCreate(name="Modèle", subject=subject, body_html=body_html)
    )


def test_each_enabled_module_says_what_it_writes(db: Session, user: User, three_modules_installed: None) -> None:
    modules = _enabled_modules(db, user)

    assert modules["card-module"] == {
        "key": "card-module",
        "label": "Cartes",
        "has_email_templates": True,
        "has_sms_templates": True,
    }
    assert modules["email-only-module"]["has_email_templates"] is True
    assert modules["email-only-module"]["has_sms_templates"] is False
    assert modules["own-messages-module"]["has_email_templates"] is False
    assert modules["own-messages-module"]["has_sms_templates"] is False


def test_a_module_switched_off_is_not_listed(db: Session, user: User, three_modules_installed: None) -> None:
    product_module_service.set_enabled(db, "card-module", False, user_id=user.id)

    assert "card-module" not in _enabled_modules(db, user)


def test_a_template_using_a_module_variable_belongs_to_that_module(
    db: Session, user: User, three_modules_installed: None
) -> None:
    linking = _template(db, user, "<p>Votre carte : {lien_carte_test}</p>")
    pricing_in_subject = _template(db, user, "<p>Bonjour</p>", subject="Votre carte à {prix_carte_test}")

    assert email_template_service.to_response(linking).module == "card-module"
    assert email_template_service.to_response(pricing_in_subject).module == "card-module"


def test_a_template_without_a_module_variable_is_a_websites_template(
    db: Session, user: User, three_modules_installed: None
) -> None:
    template = _template(db, user, "<p>Votre site : {lien_demo}</p>")

    assert email_template_service.to_response(template).module == "websites"


def test_a_module_variable_of_a_module_not_installed_leaves_the_template_to_websites(db: Session, user: User) -> None:
    template = _template(db, user, "<p>Votre carte : {lien_carte_test}</p>")

    assert email_template_service.to_response(template).module == "websites"
