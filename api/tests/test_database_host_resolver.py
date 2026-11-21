"""New database connections go to the host's last known address while its name does not resolve."""

from __future__ import annotations

import socket
from collections.abc import Callable

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError

from core.database_host_resolver import DatabaseHostResolver

DATABASE_HOST: str = "database.example.test"
LAST_KNOWN_ADDRESS: str = "127.0.0.1"
CLOSED_LOCAL_PORT: int = 9


class ResolverStandIn:
    """Answers for the database host like a working resolver, or fails like one that cannot find the name."""

    def __init__(self, real_getaddrinfo: Callable[..., list[tuple[object, ...]]]) -> None:
        self.real_getaddrinfo: Callable[..., list[tuple[object, ...]]] = real_getaddrinfo
        self.is_down: bool = False
        self.looked_up_hosts: list[str] = []

    def __call__(self, host: str, port: int, *args: object, **kwargs: object) -> list[tuple[object, ...]]:
        if host != DATABASE_HOST:
            return self.real_getaddrinfo(host, port, *args, **kwargs)
        self.looked_up_hosts.append(host)
        if self.is_down:
            raise socket.gaierror(-2, "Name or service not known")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (LAST_KNOWN_ADDRESS, port))]


@pytest.fixture
def resolver_stand_in(monkeypatch: pytest.MonkeyPatch) -> ResolverStandIn:
    """Replaces name resolution for the database host only; every other name resolves for real."""
    stand_in = ResolverStandIn(socket.getaddrinfo)
    monkeypatch.setattr(socket, "getaddrinfo", stand_in)
    return stand_in


def _new_connection_params(resolver: DatabaseHostResolver, host: str = DATABASE_HOST) -> dict[str, object]:
    connect_params: dict[str, object] = {"host": host, "port": 3306, "user": "api"}
    resolver.fall_back_to_last_known_address(None, None, [], connect_params)
    return connect_params


def test_connects_by_name_while_the_host_resolves(resolver_stand_in: ResolverStandIn) -> None:
    assert _new_connection_params(DatabaseHostResolver())["host"] == DATABASE_HOST


def test_connects_to_the_last_known_address_when_the_name_stops_resolving(resolver_stand_in: ResolverStandIn) -> None:
    resolver = DatabaseHostResolver()
    _new_connection_params(resolver)
    resolver_stand_in.is_down = True

    assert _new_connection_params(resolver)["host"] == LAST_KNOWN_ADDRESS


def test_leaves_the_usual_error_to_the_driver_without_a_known_address(resolver_stand_in: ResolverStandIn) -> None:
    resolver_stand_in.is_down = True

    assert _new_connection_params(DatabaseHostResolver())["host"] == DATABASE_HOST


def test_goes_back_to_the_name_once_it_resolves_again(resolver_stand_in: ResolverStandIn) -> None:
    resolver = DatabaseHostResolver()
    _new_connection_params(resolver)
    resolver_stand_in.is_down = True
    _new_connection_params(resolver)
    resolver_stand_in.is_down = False

    assert _new_connection_params(resolver)["host"] == DATABASE_HOST


def test_does_not_look_up_a_host_given_as_an_address(resolver_stand_in: ResolverStandIn) -> None:
    assert _new_connection_params(DatabaseHostResolver(), host="10.0.0.5")["host"] == "10.0.0.5"
    assert resolver_stand_in.looked_up_hosts == []


def test_a_real_connection_attempt_reaches_the_last_known_address(resolver_stand_in: ResolverStandIn) -> None:
    resolver = DatabaseHostResolver()
    _new_connection_params(resolver)
    resolver_stand_in.is_down = True
    engine = create_engine(
        f"mysql+pymysql://api:secret@{DATABASE_HOST}:{CLOSED_LOCAL_PORT}/devleadhunter?connect_timeout=2"
    )
    event.listen(engine, "do_connect", resolver.fall_back_to_last_known_address)

    with pytest.raises(OperationalError) as raised:
        engine.connect()

    assert f"'{LAST_KNOWN_ADDRESS}'" in str(raised.value)
    assert "Name or service not known" not in str(raised.value)
    engine.dispose()
