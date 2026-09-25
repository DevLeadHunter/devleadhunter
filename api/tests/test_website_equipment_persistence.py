"""Tests for storing the "déjà équipé" website scan on prospects.

The scan runs after a search, in the background, on its own sessions: these tests
run it against an in-memory SQLite database and a canned network layer, and check
which prospects get scanned and what lands in ``website_equipment_json``.
"""

import asyncio
import importlib
import pkgutil

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import models
import services.website_equipment_service as equipment_module
from core.database import Base
from enums.chat_widget_provider import ChatWidgetProvider
from models.prospect import Prospect
from models.prospect_db import ProspectDB
from services.website_equipment_service import WebsiteEquipment, WebsiteEquipmentService

# Load every model so SQLAlchemy can configure the mappers (relationships resolve across models).
for _module in pkgutil.iter_modules(models.__path__):
    importlib.import_module("models." + _module.name)


@pytest.fixture
def session_factory(monkeypatch: pytest.MonkeyPatch) -> sessionmaker:
    """One in-memory database shared by every session the service opens."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(equipment_module, "SessionLocal", factory)
    return factory


def _add_prospect(db: Session, name: str, website: str | None, website_status: str | None) -> ProspectDB:
    row = ProspectDB(
        name=name,
        city="Angers",
        website=website,
        website_status=website_status,
        category="Couvreur",
        source="google",
        confidence=2,
        user_id=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@pytest.mark.parametrize(
    ("website", "website_status", "expected"),
    [
        ("https://toitures-morel.fr", "live", True),
        ("https://toitures-morel.fr", None, True),
        ("https://toitures-morel.fr", "dead", False),
        ("https://morel.business.site", "placeholder", False),
        (None, None, False),
        ("   ", "live", False),
    ],
)
def test_only_live_or_unchecked_websites_are_scannable(
    website: str | None, website_status: str | None, expected: bool
) -> None:
    row = ProspectDB(name="Toitures Morel", website=website, website_status=website_status)

    assert WebsiteEquipmentService.is_scannable(row) is expected


def test_snapshot_stores_provider_slugs_and_the_form_flag() -> None:
    equipment = WebsiteEquipment(chat_providers=(ChatWidgetProvider.TIDIO,), has_contact_form=True)

    assert WebsiteEquipmentService.to_snapshot(equipment) == {"chat_providers": ["tidio"], "has_contact_form": True}


def test_refresh_prospect_persists_the_scan(session_factory: sessionmaker, monkeypatch: pytest.MonkeyPatch) -> None:
    service = WebsiteEquipmentService()

    async def fake_inspect(website: str | None) -> WebsiteEquipment:
        return WebsiteEquipment(chat_providers=(ChatWidgetProvider.CRISP,))

    monkeypatch.setattr(service, "inspect", fake_inspect)
    db = session_factory()
    row = _add_prospect(db, "Toitures Morel", "https://toitures-morel.fr", "live")

    assert asyncio.run(service.refresh_prospect(db, row)) is True
    db.refresh(row)

    assert row.website_equipment_json == {"chat_providers": ["crisp"], "has_contact_form": False}
    assert row.website_equipment_at is not None
    serialized = Prospect.model_validate(row)
    assert serialized.website_equipment_json is not None
    assert serialized.website_equipment_json.chat_providers == ["crisp"]


def test_unreadable_site_keeps_the_previous_scan(
    session_factory: sessionmaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = WebsiteEquipmentService()

    async def unreadable(website: str | None) -> None:
        return None

    monkeypatch.setattr(service, "inspect", unreadable)
    db = session_factory()
    row = _add_prospect(db, "Toitures Morel", "https://toitures-morel.fr", "live")
    row.website_equipment_json = {"chat_providers": ["tidio"], "has_contact_form": False}
    db.commit()

    assert asyncio.run(service.refresh_prospect(db, row)) is False
    db.refresh(row)

    assert row.website_equipment_json == {"chat_providers": ["tidio"], "has_contact_form": False}


def test_background_scan_updates_only_scannable_prospects(
    session_factory: sessionmaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = WebsiteEquipmentService()
    requested: list[list[str]] = []

    async def fake_inspect_many(websites: list[str]) -> dict[str, WebsiteEquipment | None]:
        requested.append(websites)
        return {
            "https://toitures-morel.fr": WebsiteEquipment(has_contact_form=True),
            "https://garage-dupont.fr": None,
        }

    monkeypatch.setattr(service, "inspect_many", fake_inspect_many)
    db = session_factory()
    live = _add_prospect(db, "Toitures Morel", "https://toitures-morel.fr", "live")
    unreadable = _add_prospect(db, "Garage Dupont", "https://garage-dupont.fr", "live")
    dead = _add_prospect(db, "Charpente Martin", "https://charpente-martin.fr", "dead")
    no_site = _add_prospect(db, "Carrosserie Leroy", None, None)
    ids = [live.id, unreadable.id, dead.id, no_site.id]
    db.close()

    asyncio.run(service._refresh_in_background(ids))

    assert requested == [["https://toitures-morel.fr", "https://garage-dupont.fr"]]
    check = session_factory()
    stored = {row.name: row.website_equipment_json for row in check.query(ProspectDB).all()}
    assert stored == {
        "Toitures Morel": {"chat_providers": [], "has_contact_form": True},
        "Garage Dupont": None,
        "Charpente Martin": None,
        "Carrosserie Leroy": None,
    }


def test_background_scan_skips_a_website_edited_meanwhile(
    session_factory: sessionmaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = WebsiteEquipmentService()
    db = session_factory()
    row = _add_prospect(db, "Toitures Morel", "https://toitures-morel.fr", "live")
    prospect_id = row.id
    db.close()

    async def edit_during_scan(websites: list[str]) -> dict[str, WebsiteEquipment | None]:
        editor = session_factory()
        edited = editor.get(ProspectDB, prospect_id)
        assert edited is not None
        edited.website = "https://nouveau-site.fr"
        editor.commit()
        editor.close()
        return {"https://toitures-morel.fr": WebsiteEquipment(chat_providers=(ChatWidgetProvider.TIDIO,))}

    monkeypatch.setattr(service, "inspect_many", edit_during_scan)

    asyncio.run(service._refresh_in_background([prospect_id]))

    check = session_factory()
    stored = check.get(ProspectDB, prospect_id)
    assert stored is not None
    assert stored.website_equipment_json is None


def test_schedule_refresh_ignores_an_empty_batch() -> None:
    service = WebsiteEquipmentService()

    service.schedule_refresh([])

    assert service._background_tasks == set()
