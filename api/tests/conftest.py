"""Shared test setup: every model registered on the metadata, an in-memory database per test, no real storage or directory."""

import importlib
import pkgutil
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import models
from core.config import settings
from core.database import Base
from services.prospect_search.swiss_directory import SwissDirectoryEntry, swiss_directory
from services.r2_storage_service import r2_storage

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

    monkeypatch.setattr(swiss_directory, "entry_for_phone", no_entry)
    monkeypatch.setattr(swiss_directory, "entries_for_name", no_entries)


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
