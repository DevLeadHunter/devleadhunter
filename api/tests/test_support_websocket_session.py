"""
Tests for the support sockets — a dashboard tab left open keeps no database connection while its socket waits.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

import api.v1.routes.support as support_routes
from core.database import Base
from models.support_ticket import SupportTicket
from models.user import User
from services.auth_service import AuthService

TICKET_ID = 3
TICKET_OWNER_ID = 7
TICKET_OWNER_EMAIL = "operateur@dibodev.fr"
OTHER_USER_ID = 8
OTHER_USER_EMAIL = "voisin@example.com"
UNKNOWN_EMAIL = "inconnu@example.com"


@pytest.fixture
def connection_pool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[QueuePool]:
    """A real connection pool on a database on disk, where a connection kept by a socket shows as checked out."""
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'support.db').as_posix()}",
        connect_args={"check_same_thread": False},
        poolclass=QueuePool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(id=TICKET_OWNER_ID, name="Dibodev", email=TICKET_OWNER_EMAIL, hashed_password="x"))
        session.add(User(id=OTHER_USER_ID, name="Voisin", email=OTHER_USER_EMAIL, hashed_password="x"))
        session.add(
            SupportTicket(id=TICKET_ID, user_id=TICKET_OWNER_ID, subject="Facture", description="Où est ma facture ?")
        )
        session.commit()
    monkeypatch.setattr(support_routes, "SessionLocal", sessionmaker(bind=engine))

    pool = engine.pool
    assert isinstance(pool, QueuePool)
    yield pool
    engine.dispose()


def _client() -> TestClient:
    """The support routes, with the sign-in check of the sockets left as it is."""
    application = FastAPI()
    application.include_router(support_routes.router)
    return TestClient(application)


def _token_of(email: str) -> str:
    """A valid access token whose subject is this email."""
    return AuthService.create_access_token(data={"sub": email})


def test_a_ticket_socket_keeps_no_database_connection_while_it_waits(connection_pool: QueuePool) -> None:
    with _client().websocket_connect(f"/support/tickets/{TICKET_ID}/ws?token={_token_of(TICKET_OWNER_EMAIL)}"):
        assert connection_pool.checkedout() == 0


def test_the_ticket_list_socket_keeps_no_database_connection_while_it_waits(connection_pool: QueuePool) -> None:
    with _client().websocket_connect(f"/support/tickets/ws?token={_token_of(TICKET_OWNER_EMAIL)}"):
        assert connection_pool.checkedout() == 0


def test_a_ticket_socket_refused_to_another_user_gives_its_database_connection_back(
    connection_pool: QueuePool,
) -> None:
    refused_socket: Any = SimpleNamespace()

    with pytest.raises(HTTPException) as refusal:
        asyncio.run(support_routes.ticket_websocket(refused_socket, TICKET_ID, token=_token_of(OTHER_USER_EMAIL)))

    assert refusal.value.status_code == status.HTTP_403_FORBIDDEN
    assert connection_pool.checkedout() == 0


def test_the_ticket_list_socket_refused_to_an_unknown_user_gives_its_database_connection_back(
    connection_pool: QueuePool,
) -> None:
    refused_socket: Any = SimpleNamespace()

    with pytest.raises(HTTPException) as refusal:
        asyncio.run(support_routes.global_tickets_websocket(refused_socket, token=_token_of(UNKNOWN_EMAIL)))

    assert refusal.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert connection_pool.checkedout() == 0
