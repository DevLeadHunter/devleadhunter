"""
Unit tests for sending-identity resolution.

These exercise the provider-selection logic in isolation: the DB-touching
query helpers (``_resend_config`` / ``_default_gmail_account``) and
``get_active_provider`` are stubbed, so the tests assert the routing decision
without a database — matching the pure-logic style of the rest of the suite.
"""
from types import SimpleNamespace

import pytest

import services.sending_identity as si
from enums.sending_provider import SendingProvider
from services.sending_identity import (
    SendingNotConfiguredError,
    describe_sending_config,
    get_active_provider,
    resolve_sending_identity,
)


class _FakeDB:
    """Minimal stand-in exposing only ``get`` (used by get_active_provider)."""

    def __init__(self, user: object | None) -> None:
        self._user = user

    def get(self, _model: object, _pk: int) -> object | None:
        return self._user


def test_get_active_provider_defaults_to_resend() -> None:
    """A missing user (or unset column) falls back to Resend."""
    assert get_active_provider(_FakeDB(user=None), 1) == SendingProvider.RESEND.value


def test_get_active_provider_normalizes_unknown_value() -> None:
    """An unexpected stored value is normalised back to Resend."""
    db = _FakeDB(user=SimpleNamespace(sending_provider="bogus"))
    assert get_active_provider(db, 1) == SendingProvider.RESEND.value


def test_get_active_provider_reads_gmail() -> None:
    """A stored ``gmail`` value is honoured."""
    db = _FakeDB(user=SimpleNamespace(sending_provider="gmail"))
    assert get_active_provider(db, 1) == SendingProvider.GMAIL.value


def test_resolve_resend_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resend provider resolves to a decrypted key + configured from-address."""
    monkeypatch.setattr(si, "get_active_provider", lambda db, uid: SendingProvider.RESEND.value)
    monkeypatch.setattr(
        si,
        "_resend_config",
        lambda db, uid: SimpleNamespace(api_key="enc", from_email="leo@mail.dibodev.fr", from_name="Léo"),
    )
    monkeypatch.setattr(si.encryption_service, "decrypt", lambda value: "re_plain")

    identity = resolve_sending_identity(None, 1)

    assert identity.provider == SendingProvider.RESEND.value
    assert identity.from_email == "leo@mail.dibodev.fr"
    assert identity.from_name == "Léo"
    assert identity.resend_api_key == "re_plain"
    assert identity.gmail_account is None


def test_resolve_resend_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resend selected but not configured raises SendingNotConfiguredError."""
    monkeypatch.setattr(si, "get_active_provider", lambda db, uid: SendingProvider.RESEND.value)
    monkeypatch.setattr(si, "_resend_config", lambda db, uid: None)

    with pytest.raises(SendingNotConfiguredError):
        resolve_sending_identity(None, 1)


def test_resolve_gmail_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gmail provider resolves to the chosen account, with no Resend key."""
    account = SimpleNamespace(id=7, email="me@gmail.com", name="Me")
    monkeypatch.setattr(si, "get_active_provider", lambda db, uid: SendingProvider.GMAIL.value)
    monkeypatch.setattr(si, "_default_gmail_account", lambda db, uid: account)

    identity = resolve_sending_identity(None, 1)

    assert identity.provider == SendingProvider.GMAIL.value
    assert identity.gmail_account is account
    assert identity.from_email == "me@gmail.com"
    assert identity.resend_api_key is None


def test_resolve_gmail_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gmail selected but no connected account raises SendingNotConfiguredError."""
    monkeypatch.setattr(si, "get_active_provider", lambda db, uid: SendingProvider.GMAIL.value)
    monkeypatch.setattr(si, "_default_gmail_account", lambda db, uid: None)

    with pytest.raises(SendingNotConfiguredError):
        resolve_sending_identity(None, 1)


def test_describe_sending_config_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """The settings summary reports the active provider + both readiness flags."""
    monkeypatch.setattr(si, "get_active_provider", lambda db, uid: SendingProvider.GMAIL.value)
    monkeypatch.setattr(
        si, "_resend_config", lambda db, uid: SimpleNamespace(api_key="enc", from_email="leo@mail.dibodev.fr")
    )
    monkeypatch.setattr(si, "_default_gmail_account", lambda db, uid: SimpleNamespace(email="me@gmail.com"))

    assert describe_sending_config(None, 1) == {
        "provider": "gmail",
        "resend_configured": True,
        "resend_from_email": "leo@mail.dibodev.fr",
        "gmail_configured": True,
        "gmail_email": "me@gmail.com",
    }
