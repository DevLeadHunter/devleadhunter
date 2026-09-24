"""Shared test setup: every model registered on the metadata, and an in-memory database per test."""

import importlib
import pkgutil
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import models
from core.database import Base

for _module in pkgutil.iter_modules(models.__path__):
    importlib.import_module("models." + _module.name)


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
