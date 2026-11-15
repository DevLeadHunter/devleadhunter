"""Each sent SMS is filed under the module that sent it, and the SMS tracking reads one module at a time."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import ClassVar

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import services.sms_service as sms_module
from api.v1.routes.sms import router as sms_router
from core.database import get_db
from core.product_modules.campaign_offer import CampaignOffer
from core.product_modules.contract import ProductModule
from core.product_modules.module_at_work import ModuleAtWork
from core.product_modules.registry import product_module_registry
from enums.sms_status import SmsStatus
from enums.sms_template_category import SmsTemplateCategory
from migrations.add_sms_message_module_key import run_migration
from models.campaign import Campaign, CampaignStatus
from models.email_queue import EmailQueue
from models.prospect_db import ProspectDB
from models.sms_config import SmsConfig
from models.sms_message import SmsMessage
from models.user import User
from services.auth_service import get_current_user
from services.sms.templates import SmsTemplate
from services.sms_service import SmsSendOutcome, SmsService
from tests.sms_fakes import AcceptingSmsProvider, AsyncCallRecorder

_USER_ID = 7
_MODULE_KEY = "texting-module"
_MODULE_PAGE_LINK = "offre.example/p/"
_TEMPLATES: dict[str, SmsTemplate] = {
    "site": SmsTemplate(
        key="site",
        name="Site",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body="{salutation}, un site pour {entreprise} : {lien_demo} {signature}",
    ),
    "offre": SmsTemplate(
        key="offre",
        name="Offre",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body="{salutation}, {offre_ecrite} pour {entreprise} {signature}",
    ),
}


class _TextingOffer(CampaignOffer):
    """An offer sold by SMS with ``{offre_ecrite}``, whose pages are linked under ``offre.example/p/``."""

    module_key: ClassVar[str] = _MODULE_KEY
    offer_label: ClassVar[str] = "texted offer"
    expired_offer_skip_reason: ClassVar[str] = "Offre expirée"
    sms_offer_variables: ClassVar[tuple[str, ...]] = ("offre_ecrite",)
    missing_offer_skip_reason: ClassVar[str] = "Pas d'offre"
    missing_offer_launch_summary: ClassVar[str] = "faute d'offre"

    def has_active_offer(self, db: Session, *, prospect_id: int, user_id: int) -> bool:
        """Every prospect has the offer."""
        return True

    def sms_variables(self, db: Session, prospect: ProspectDB, *, user_id: int) -> dict[str, str]:
        """The offer, in a few words."""
        return {"offre_ecrite": "une offre"}

    def owns_sms_message(self, message: SmsMessage) -> bool:
        """An SMS that links one of the offer's pages."""
        return _MODULE_PAGE_LINK in (message.body or "")


class _TextingModule(ProductModule):
    """A module that texts its own prospects."""

    key: ClassVar[str] = _MODULE_KEY
    label: ClassVar[str] = "Module qui écrit par SMS"
    enabled_by_default: ClassVar[bool] = True

    def campaign_offer(self) -> CampaignOffer:
        """The texted offer."""
        return _TextingOffer()


@pytest.fixture(autouse=True)
def texting_module_installed() -> Iterator[None]:
    product_module_registry.use([_TextingModule()])
    yield


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> AcceptingSmsProvider:
    monkeypatch.setattr(SmsService, "legal_window_refusal", lambda self, country=None: None)
    monkeypatch.setattr(sms_module.notification_service, "notify_sms_event", AsyncCallRecorder())
    monkeypatch.setattr(sms_module, "find_sms_template", _TEMPLATES.get)
    return AcceptingSmsProvider()


def _config(db: Session) -> SmsConfig:
    config = SmsConfig(user_id=_USER_ID, sender="Dibodev")
    db.add(config)
    db.commit()
    return config


def _prospect(db: Session) -> ProspectDB:
    prospect = ProspectDB(
        name="Garage Martin",
        category="Garage automobile",
        phone="06 11 22 33 44",
        country="FR",
        source="google",
        confidence=2,
        user_id=_USER_ID,
    )
    db.add(prospect)
    db.commit()
    return prospect


def _filed_module(outcome: SmsSendOutcome) -> str:
    assert outcome.sent, outcome.reason
    assert outcome.message is not None
    return outcome.message.module_key


def _send_from_template(db: Session, provider: AcceptingSmsProvider, template_key: str) -> SmsSendOutcome:
    return asyncio.run(
        SmsService(provider=provider).send_to_prospect(
            db,
            user_id=_USER_ID,
            prospect=_prospect(db),
            config=_config(db),
            demo_url="https://demo.dibodev.fr/s/garage-martin",
            cold=True,
            template_key=template_key,
        )
    )


def _send_free_text(
    db: Session, provider: AcceptingSmsProvider, text: str, *, written_from_module_key: str | None = None
) -> SmsSendOutcome:
    return asyncio.run(
        SmsService(provider=provider).send_manual(
            db,
            user_id=_USER_ID,
            config=_config(db),
            to_raw="06 11 22 33 44",
            text=text,
            written_from_module_key=written_from_module_key,
        )
    )


def _message(db: Session, module_key: str, *, body: str = "Bonjour", price_cents: int = 6) -> SmsMessage:
    message = SmsMessage(
        user_id=_USER_ID,
        to_e164="+33611223344",
        sender="Dibodev",
        body=body,
        status=SmsStatus.DELIVERED.value,
        price_cents=price_cents,
        module_key=module_key,
    )
    db.add(message)
    db.commit()
    return message


def _tracking_client(db: Session) -> TestClient:
    app = FastAPI()
    app.include_router(sms_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: User(
        id=_USER_ID, name="Léo", email="leo@example.com", hashed_password="x"
    )
    return TestClient(app)


def test_a_template_sms_is_filed_under_the_module_of_its_template(db: Session, provider: AcceptingSmsProvider) -> None:
    assert _filed_module(_send_from_template(db, provider, "offre")) == _MODULE_KEY


def test_a_websites_template_sms_is_filed_under_the_websites_module(
    db: Session, provider: AcceptingSmsProvider
) -> None:
    assert _filed_module(_send_from_template(db, provider, "site")) == "websites"


def test_a_free_text_sms_is_filed_under_the_module_it_was_written_from(
    db: Session, provider: AcceptingSmsProvider
) -> None:
    outcome = _send_free_text(db, provider, "Bonjour, un essai", written_from_module_key=_MODULE_KEY)

    assert _filed_module(outcome) == _MODULE_KEY


def test_a_free_text_sms_written_from_no_module_is_filed_under_the_websites_module(
    db: Session, provider: AcceptingSmsProvider
) -> None:
    assert _filed_module(_send_free_text(db, provider, "Bonjour, un essai")) == "websites"


def test_an_sms_linking_a_module_page_is_filed_under_that_module_wherever_it_was_written(
    db: Session, provider: AcceptingSmsProvider
) -> None:
    outcome = _send_free_text(
        db, provider, f"Votre page : {_MODULE_PAGE_LINK}garage-martin", written_from_module_key="websites"
    )

    assert _filed_module(outcome) == _MODULE_KEY


def test_a_service_sms_sent_while_a_module_is_at_work_is_filed_under_it(
    db: Session, provider: AcceptingSmsProvider
) -> None:
    with ModuleAtWork.during("alerting-module"):
        outcome = asyncio.run(
            SmsService(provider=provider).send_service_message(
                db,
                user_id=_USER_ID,
                config=_config(db),
                to_e164="+33611223344",
                text="Nouvelle demande",
                recipient_name="Garage Martin",
            )
        )

    assert _filed_module(outcome) == "alerting-module"


@pytest.mark.parametrize(
    ("module_open_in_the_dashboard", "filed_module"),
    [(_MODULE_KEY, _MODULE_KEY), ("module-not-installed", "websites"), (None, "websites")],
)
def test_a_hand_written_sms_is_filed_under_the_module_open_in_the_dashboard(
    db: Session,
    provider: AcceptingSmsProvider,
    monkeypatch: pytest.MonkeyPatch,
    module_open_in_the_dashboard: str | None,
    filed_module: str,
) -> None:
    monkeypatch.setattr(sms_module.sms_service, "_provider", provider)
    _config(db)

    response = _tracking_client(db).post(
        "/api/v1/sms/send",
        json={"to": "06 11 22 33 44", "text": "Bonjour, un essai", "module_key": module_open_in_the_dashboard},
    )

    assert response.json()["sent"] is True
    [message] = db.query(SmsMessage).all()
    assert message.module_key == filed_module


def test_the_sms_tracking_lists_one_module_at_a_time(db: Session) -> None:
    _message(db, "websites", body="Un site")
    _message(db, _MODULE_KEY, body="Une offre")
    client = _tracking_client(db)

    module_messages = client.get("/api/v1/sms/messages", params={"module_key": _MODULE_KEY}).json()
    every_message = client.get("/api/v1/sms/messages").json()

    assert [message["body"] for message in module_messages["messages"]] == ["Une offre"]
    assert every_message["total"] == 2


def test_the_sms_figures_count_one_module_at_a_time(db: Session) -> None:
    _message(db, "websites", price_cents=6)
    _message(db, "websites", price_cents=6)
    _message(db, _MODULE_KEY, price_cents=13)
    client = _tracking_client(db)

    module_stats = client.get("/api/v1/sms/stats", params={"module_key": _MODULE_KEY}).json()
    websites_stats = client.get("/api/v1/sms/stats", params={"module_key": "websites"}).json()

    assert (module_stats["total"], module_stats["cost_cents"]) == (1, 13)
    assert (websites_stats["total"], websites_stats["cost_cents"]) == (2, 12)


def test_the_migration_files_the_sms_already_sent_under_their_module(
    db: Session, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("migrations.add_sms_message_module_key.find_sms_template", _TEMPLATES.get)
    prospect = _prospect(db)
    module_campaign = Campaign(
        user_id=_USER_ID, name="Offre", status=CampaignStatus.ACTIVE, channel="sms", sms_template_key="offre"
    )
    websites_campaign = Campaign(
        user_id=_USER_ID, name="Sites", status=CampaignStatus.ACTIVE, channel="sms", sms_template_key="site"
    )
    db.add_all([module_campaign, websites_campaign])
    db.flush()
    module_campaign_sms = _message(db, "websites", body="Une offre pour Garage Martin")
    websites_campaign_sms = _message(db, "websites", body="Un site pour Garage Martin")
    module_page_sms = _message(db, "websites", body=f"Votre page : {_MODULE_PAGE_LINK}garage-martin")
    free_text_sms = _message(db, "websites", body="Bonjour, un essai")
    for campaign, message in ((module_campaign, module_campaign_sms), (websites_campaign, websites_campaign_sms)):
        db.add(
            EmailQueue(
                user_id=_USER_ID,
                campaign_id=campaign.id,
                prospect_id=prospect.id,
                scheduled_at=message.created_at,
                sms_message_id=message.id,
                status="sent",
            )
        )
    db.commit()

    run_migration(engine)
    db.expire_all()

    assert module_campaign_sms.module_key == _MODULE_KEY
    assert websites_campaign_sms.module_key == "websites"
    assert module_page_sms.module_key == _MODULE_KEY
    assert free_text_sms.module_key == "websites"
