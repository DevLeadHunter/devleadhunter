"""Each sent email is filed under the module that sent it, and the email tracking reads one module at a time."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any, ClassVar

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Integer
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, Session, mapped_column

from api.v1.product_module_mounting import include_product_module_routers
from api.v1.routes.emails import router as emails_router
from core.database import Base, get_db
from core.product_modules.campaign_offer import CampaignOffer
from core.product_modules.contract import BackgroundLoop, ProductModule
from core.product_modules.module_at_work import ModuleAtWork
from core.product_modules.registry import ProductModuleRegistry, product_module_registry
from enums.email_status import EmailStatus
from migrations.add_email_log_module_key import run_migration
from models.campaign import Campaign, CampaignStatus
from models.email_log import EmailLog
from models.email_reply import EmailReply
from models.email_template import EmailTemplate
from models.user import User
from services import email_sending_service as email_sending
from services import reply_inbox_forward_service, sending_identity
from services.auth_service import get_current_user
from services.email_sending_service import EmailSendingService
from services.product_module_loop_supervisor import ProductModuleLoopSupervisor
from services.product_module_service import ProductModuleService

_MODULE_KEY = "writing-module"
_module_router = APIRouter()
_modules_seen_by_the_loop: list[str | None] = []


@_module_router.get("/writing-module/module-at-work")
async def _read_module_at_work() -> dict[str, str | None]:
    return {"module": ModuleAtWork.key()}


async def _record_module_at_work() -> None:
    _modules_seen_by_the_loop.append(ModuleAtWork.key())


class _WrittenMessage(Base):
    """A message of the writing module, which keeps the email it sent."""

    __tablename__ = "writing_module_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email_log_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class _WritingOffer(CampaignOffer):
    """An offer sold by email, linked by ``{lien_offre_ecrite}``."""

    module_key: ClassVar[str] = _MODULE_KEY
    offer_label: ClassVar[str] = "written offer"
    expired_offer_skip_reason: ClassVar[str] = "Offre expirée"
    email_link_variables: ClassVar[tuple[str, ...]] = ("lien_offre_ecrite",)
    email_offer_variables: ClassVar[tuple[str, ...]] = ("lien_offre_ecrite",)
    missing_offer_skip_reason: ClassVar[str] = "Pas d'offre"
    missing_offer_launch_summary: ClassVar[str] = "faute d'offre"


class _WritingModule(ProductModule):
    """A module that writes to its own prospects from its routes and its loops, and sells by campaign too."""

    key: ClassVar[str] = _MODULE_KEY
    label: ClassVar[str] = "Module qui écrit"
    enabled_by_default: ClassVar[bool] = True

    def routers(self) -> list[APIRouter]:
        """The module's single route."""
        return [_module_router]

    def background_loops(self) -> list[BackgroundLoop]:
        """The module's single loop."""
        return [_record_module_at_work]

    def campaign_offer(self) -> CampaignOffer:
        """The written offer."""
        return _WritingOffer()


@pytest.fixture
def writing_module_installed() -> Iterator[None]:
    product_module_registry.use([_WritingModule()])
    yield


@pytest.fixture
def sender(db: Session) -> User:
    user = User(name="Léo", email="leo@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    return user


def _send(db: Session, sender: User, **options: Any) -> EmailLog:
    result = asyncio.run(
        EmailSendingService(db).send_via_user_identity(
            user_id=sender.id,
            recipient_email="contact@entreprise.example",
            subject="Bonjour",
            body_html="<p>Bonjour</p>",
            is_transactional=True,
            **options,
        )
    )
    assert result["success"] is True
    log: EmailLog | None = db.get(EmailLog, result["email_log_id"])
    assert log is not None
    return log


def _log(db: Session, sender: User, module_key: str, *, status: EmailStatus = EmailStatus.DELIVERED) -> EmailLog:
    log = EmailLog(
        user_id=sender.id,
        recipient_email="contact@entreprise.example",
        subject=f"Email de {module_key}",
        body_html="<p>Bonjour</p>",
        status=status.value,
        provider="resend",
        module_key=module_key,
    )
    db.add(log)
    db.commit()
    return log


def _tracking_client(db: Session, sender: User) -> TestClient:
    app = FastAPI()
    app.include_router(emails_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: sender
    return TestClient(app)


def test_a_module_route_runs_with_its_module_at_work(db: Session, writing_module_installed: None) -> None:
    router = APIRouter()
    include_product_module_routers(router)

    @router.get("/core/module-at-work")
    async def read_module_at_work() -> dict[str, str | None]:
        return {"module": ModuleAtWork.key()}

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    assert client.get("/writing-module/module-at-work").json() == {"module": _MODULE_KEY}
    assert client.get("/core/module-at-work").json() == {"module": None}


def test_a_module_loop_runs_with_its_module_at_work(db: Session) -> None:
    registry = ProductModuleRegistry()
    registry.use([_WritingModule()])
    supervisor = ProductModuleLoopSupervisor(
        registry, ProductModuleService(registry), session_factory=lambda: _NonClosingSession(db)
    )
    _modules_seen_by_the_loop.clear()

    async def scenario() -> None:
        supervisor.reconcile()
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    asyncio.run(scenario())

    assert _modules_seen_by_the_loop == [_MODULE_KEY]
    assert ModuleAtWork.key() is None


def test_an_email_sent_by_the_core_is_filed_under_the_websites_module(
    db: Session, sender: User, resend_payloads: list[dict[str, Any]]
) -> None:
    assert _send(db, sender).module_key == "websites"


def test_an_email_sent_while_a_module_is_at_work_is_filed_under_it(
    db: Session, sender: User, resend_payloads: list[dict[str, Any]]
) -> None:
    with ModuleAtWork.during(_MODULE_KEY):
        log = _send(db, sender)

    assert log.module_key == _MODULE_KEY
    assert ModuleAtWork.key() is None


def test_a_named_module_wins_over_the_module_at_work(
    db: Session, sender: User, resend_payloads: list[dict[str, Any]]
) -> None:
    with ModuleAtWork.during(_MODULE_KEY):
        log = _send(db, sender, module_key="another-module")

    assert log.module_key == "another-module"


@pytest.mark.parametrize(
    ("module_open_in_the_dashboard", "filed_module"),
    [(_MODULE_KEY, _MODULE_KEY), ("module-not-installed", "websites"), (None, "websites")],
)
def test_a_hand_written_email_is_filed_under_the_module_open_in_the_dashboard(
    db: Session,
    sender: User,
    resend_payloads: list[dict[str, Any]],
    writing_module_installed: None,
    monkeypatch: pytest.MonkeyPatch,
    module_open_in_the_dashboard: str | None,
    filed_module: str,
) -> None:
    monkeypatch.setattr(sending_identity, "resolve_sending_identity", email_sending.resolve_sending_identity)
    monkeypatch.setattr(reply_inbox_forward_service, "inbox_copy_address", lambda _identity: None)

    response = _tracking_client(db, sender).post(
        "/api/v1/emails/quick-send",
        json={
            "recipient_email": "contact@entreprise.example",
            "subject": "Bonjour",
            "body_html": "<p>Bonjour</p>",
            "module_key": module_open_in_the_dashboard,
        },
    )

    log: EmailLog | None = db.get(EmailLog, response.json()["email_log_id"])
    assert log is not None
    assert log.module_key == filed_module


def test_the_email_tracking_lists_one_module_at_a_time(db: Session, sender: User) -> None:
    _log(db, sender, "websites")
    _log(db, sender, _MODULE_KEY)
    _log(db, sender, _MODULE_KEY, status=EmailStatus.BOUNCED)
    client = _tracking_client(db, sender)

    module_logs = client.get("/api/v1/emails/logs", params={"module_key": _MODULE_KEY}).json()
    every_log = client.get("/api/v1/emails/logs").json()

    assert module_logs["total"] == 2
    assert {log["subject"] for log in module_logs["logs"]} == {f"Email de {_MODULE_KEY}"}
    assert every_log["total"] == 3


def test_the_email_figures_count_one_module_at_a_time(db: Session, sender: User) -> None:
    _log(db, sender, "websites")
    _log(db, sender, "websites")
    _log(db, sender, _MODULE_KEY)
    client = _tracking_client(db, sender)

    module_stats = client.get("/api/v1/emails/stats", params={"module_key": _MODULE_KEY}).json()
    websites_stats = client.get("/api/v1/emails/stats", params={"module_key": "websites"}).json()

    assert module_stats["total_delivered"] == 1
    assert websites_stats["total_delivered"] == 2


def test_the_replies_to_handle_are_those_of_the_module_emails(db: Session, sender: User) -> None:
    websites_log = _log(db, sender, "websites")
    module_log = _log(db, sender, _MODULE_KEY)
    for log in (websites_log, module_log):
        db.add(
            EmailReply(
                email_log_id=log.id,
                user_id=sender.id,
                from_email="contact@entreprise.example",
                subject=f"RE: {log.subject}",
                body_text="D'accord",
                resend_email_id=f"reply-{log.id}",
                matched_by="token",
            )
        )
    db.commit()
    client = _tracking_client(db, sender)

    module_replies = client.get("/api/v1/emails/replies/pending", params={"module_key": _MODULE_KEY}).json()
    every_reply = client.get("/api/v1/emails/replies/pending").json()

    assert [item["email_log_id"] for item in module_replies["items"]] == [module_log.id]
    assert every_reply["count"] == 2


def test_the_migration_files_a_campaign_email_under_its_campaign_module(
    db: Session, engine: Engine, sender: User, writing_module_installed: None
) -> None:
    module_template = EmailTemplate(
        user_id=sender.id, name="Offre", subject="Votre offre", body_html="<p>{lien_offre_ecrite}</p>"
    )
    websites_template = EmailTemplate(
        user_id=sender.id, name="Site", subject="Votre site", body_html="<p>{lien_demo}</p>"
    )
    db.add_all([module_template, websites_template])
    db.flush()
    module_campaign = Campaign(
        user_id=sender.id, name="Offre", status=CampaignStatus.ACTIVE, channel="email", template_id=module_template.id
    )
    websites_campaign = Campaign(
        user_id=sender.id, name="Sites", status=CampaignStatus.ACTIVE, channel="email", template_id=websites_template.id
    )
    db.add_all([module_campaign, websites_campaign])
    db.flush()
    module_campaign_log = _log(db, sender, "websites")
    websites_campaign_log = _log(db, sender, "websites")
    handwritten_log = _log(db, sender, "websites")
    module_campaign_log.campaign_id = module_campaign.id
    websites_campaign_log.campaign_id = websites_campaign.id
    db.commit()

    run_migration(engine)
    db.expire_all()

    assert module_campaign_log.module_key == _MODULE_KEY
    assert websites_campaign_log.module_key == "websites"
    assert handwritten_log.module_key == "websites"


def test_the_migration_files_an_email_named_by_a_module_table_under_that_module(
    db: Session, engine: Engine, sender: User, writing_module_installed: None
) -> None:
    module_email = _log(db, sender, "websites")
    core_email = _log(db, sender, "websites")
    db.add(_WrittenMessage(email_log_id=module_email.id))
    db.commit()

    run_migration(engine)
    db.expire_all()

    assert module_email.module_key == _MODULE_KEY
    assert core_email.module_key == "websites"


class _NonClosingSession:
    """The test's session behind a ``with`` block that must not close it."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def __enter__(self) -> Session:
        return self._session

    def __exit__(self, *exc_info: object) -> None:
        return None
