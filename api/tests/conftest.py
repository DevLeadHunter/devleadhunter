"""Shared test setup: every model registered on the metadata, an in-memory database per test, no real storage, directory or register."""

import importlib
import pkgutil
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import models
import services.email_sending_service as sending
import services.prospect_search.swiss_directory as swiss_directory_module
from core.config import settings
from core.database import Base
from enums.sending_provider import SendingProvider
from scrappers.google_website_button import google_website_button
from services.city_geocoding_service import CityGeocodingService
from services.decision_maker.french_departments import FrenchDepartments
from services.email_sending_service import EmailSendingService
from services.prospect_search.french_registry import FrenchRegistry
from services.prospect_search.swiss_directory import SwissDirectoryEntry, swiss_directory
from services.prospect_search.swiss_registry import SwissRegisterFirm, swiss_registry
from services.r2_storage_service import r2_storage
from services.resend_service import ResendService

for _module in pkgutil.iter_modules(models.__path__):
    importlib.import_module("models." + _module.name)


@pytest.fixture(autouse=True)
def storage_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Storage as in CI, unconfigured unless a test fakes it: a local run never touches the developer's real bucket."""
    monkeypatch.setattr(settings, "r2_endpoint", None)
    monkeypatch.setattr(r2_storage, "_client", None)


@pytest.fixture(autouse=True)
def swiss_directory_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Swiss directory lists nobody unless a test scripts an entry: a run never calls search.ch."""

    async def no_entry(phone: str | None) -> SwissDirectoryEntry | None:
        return None

    async def no_entries(name: str, town: str) -> list[SwissDirectoryEntry]:
        return []

    async def no_entries_at_address(name_word: str, address: str) -> list[SwissDirectoryEntry]:
        return []

    async def no_entry_page(entry_url: str) -> SwissDirectoryEntry | None:
        return None

    async def no_zip_asterisk(phone: str | None) -> str | None:
        return None

    monkeypatch.setattr(swiss_directory, "entry_for_phone", no_entry)
    monkeypatch.setattr(swiss_directory, "entries_for_name", no_entries)
    monkeypatch.setattr(swiss_directory, "entries_at_address", no_entries_at_address)
    monkeypatch.setattr(swiss_directory, "entry_at", no_entry_page)
    monkeypatch.setattr(swiss_directory, "zip_listing_with_asterisk", no_zip_asterisk)
    monkeypatch.setattr(swiss_directory_module, "_SECONDS_BETWEEN_REQUESTS", 0.0)
    monkeypatch.setattr(swiss_directory_module, "_SECONDS_AFTER_REFUSAL", 0.0)


@pytest.fixture(autouse=True)
def swiss_registry_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """The federal company register lists nobody unless a test scripts a firm: a run never calls Zefix."""

    async def no_firm(name: str, *, max_entries: int = 10) -> list[SwissRegisterFirm]:
        return []

    async def no_address(firm: SwissRegisterFirm) -> tuple[None, None]:
        return None, None

    async def no_page(firm: SwissRegisterFirm) -> dict[str, object]:
        return {}

    monkeypatch.setattr(swiss_registry, "firms_named", no_firm)
    monkeypatch.setattr(swiss_registry, "address_of", no_address)
    monkeypatch.setattr(swiss_registry, "_detail", no_page)


@pytest.fixture(autouse=True)
def french_registry_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """The French company registry lists nobody unless a test scripts it: a search never calls it."""

    async def no_company(query: str, **_options: object) -> list[dict[str, object]]:
        return []

    monkeypatch.setattr(FrenchRegistry, "_companies", staticmethod(no_company))


@pytest.fixture(autouse=True)
def french_communes_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """The official list of communes answers nothing unless a test scripts it: a run never calls geo.api.gouv.fr."""

    async def no_answer(town: str) -> None:
        return None

    monkeypatch.setattr(FrenchDepartments, "_communes_named", staticmethod(no_answer))
    monkeypatch.setattr(FrenchDepartments, "_department_by_town", {})
    monkeypatch.setattr(FrenchDepartments, "_is_town_by_word", {})


@pytest.fixture(autouse=True)
def city_geocoders_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """The town geocoders never answer unless a test scripts them: a run never calls geo.api.gouv.fr nor Photon."""

    async def no_answer(client: object, url: str, params: dict[str, str | int]) -> None:
        return None

    monkeypatch.setattr(CityGeocodingService, "_get_json", staticmethod(no_answer))
    monkeypatch.setattr(CityGeocodingService, "_RETRY_DELAY_SECONDS", 0.0)


@pytest.fixture(autouse=True)
def google_website_buttons_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """A card's « Site Web » button leads nowhere unless a test scripts it: a run never calls google.com."""

    async def nowhere(link: str | None) -> str | None:
        return None

    monkeypatch.setattr(google_website_button, "destination", nowhere)


@pytest.fixture
def engine() -> Engine:
    """An empty in-memory SQLite database with every table."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """A session on the test's database, closed afterwards."""
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def resend_payloads(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """The payloads handed to Resend, the sending identity and the funnel capture being stubbed."""
    payloads: list[dict[str, Any]] = []

    async def send_email(_self: ResendService, **kwargs: Any) -> dict[str, str]:
        payloads.append(kwargs)
        return {"message_id": f"msg_{len(payloads)}", "provider": "resend"}

    async def no_capture(_self: EmailSendingService, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(
        sending,
        "resolve_sending_identity",
        lambda _db, _user_id: SimpleNamespace(
            provider=SendingProvider.RESEND.value,
            gmail_account=None,
            from_email="jean@mail.example.com",
            from_name="Jean",
            resend_api_key="re_test",
        ),
    )
    monkeypatch.setattr(sending.settings, "dev_email_redirect", None)
    monkeypatch.setattr(ResendService, "send_email", send_email)
    monkeypatch.setattr(EmailSendingService, "_capture_email_sent", no_capture)
    return payloads
