"""The Google clients over HTTP: Google is never called, its answers come from an httpx MockTransport."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

import services.ai_assistant.google_calendar_client as google_module
import services.google_oauth_client as oauth_module
from services.ai_assistant.google_calendar_client import CalendarEventState, GoogleCalendarClient
from services.gmail_oauth_service import GmailOAuthService
from services.google_oauth_client import GoogleOAuthError, google_oauth_client
from services.postmaster_oauth_service import POSTMASTER_SCOPE, USERINFO_EMAIL_SCOPE, PostmasterOAuthService


def _calendar_client_with(handler: Any, monkeypatch: pytest.MonkeyPatch) -> GoogleCalendarClient:
    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def patched_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(google_module.httpx, "AsyncClient", patched_client)
    monkeypatch.setattr(google_module.settings, "google_client_id", "client-id")
    monkeypatch.setattr(google_module.settings, "google_client_secret", "client-secret")
    return GoogleCalendarClient()


def test_the_calendar_client_reads_back_an_event_it_created(monkeypatch: pytest.MonkeyPatch) -> None:
    """The reminder and the booking recovery read our event: still there, moved, cancelled or gone."""
    requested: list[str] = []
    answers = iter(
        [
            httpx.Response(200, json={"status": "confirmed", "start": {"dateTime": "2026-09-24T14:00:00+02:00"}}),
            httpx.Response(200, json={"status": "cancelled"}),
            httpx.Response(410, json={"error": {"message": "Resource has been deleted"}}),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.raw_path.decode())
        return next(answers)

    client = _calendar_client_with(handler, monkeypatch)
    standing = asyncio.run(client.get_event("a", "agenda du garage@group.calendar.google.com", "dlh1abc"))
    cancelled = asyncio.run(client.get_event("a", "primary", "dlh1abc"))
    deleted = asyncio.run(client.get_event("a", "primary", "dlh1abc"))

    assert standing == CalendarEventState(cancelled=False, start=datetime(2026, 9, 24, 12, 0))
    assert cancelled == CalendarEventState(cancelled=True, start=None)
    assert deleted is None
    assert requested[0] == "/calendar/v3/calendars/agenda%20du%20garage%40group.calendar.google.com/events/dlh1abc"


@pytest.fixture
def google_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """The server's Google OAuth client, with one redirect address per integration."""
    monkeypatch.setattr(oauth_module.settings, "google_client_id", "client-id")
    monkeypatch.setattr(oauth_module.settings, "google_client_secret", "client-secret")
    monkeypatch.setattr(oauth_module.settings, "google_redirect_uri", "https://api.test/gmail/callback")
    monkeypatch.setattr(oauth_module.settings, "google_postmaster_redirect_uri", "https://api.test/postmaster/callback")
    monkeypatch.setattr(oauth_module.settings, "google_calendar_redirect_uri", "https://api.test/calendar/callback")


def _serve_google(handler: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Answer every Google call of the shared OAuth client through a mock transport."""
    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def patched_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(oauth_module.httpx, "AsyncClient", patched_client)


def _query(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


@pytest.mark.usefixtures("google_settings")
def test_each_integration_asks_its_own_scopes_and_redirect_address() -> None:
    gmail = _query(GmailOAuthService().get_authorization_url(state="user_7"))
    postmaster = _query(PostmasterOAuthService().get_authorization_url("postmaster_user_7"))
    calendar = _query(GoogleCalendarClient.authorization_url("7.123.sig"))

    assert gmail["scope"] == ["https://www.googleapis.com/auth/gmail.send"]
    assert gmail["redirect_uri"] == ["https://api.test/gmail/callback"] and gmail["state"] == ["user_7"]
    assert postmaster["scope"] == [f"openid {USERINFO_EMAIL_SCOPE} {POSTMASTER_SCOPE}"]
    assert postmaster["redirect_uri"] == ["https://api.test/postmaster/callback"]
    assert calendar["redirect_uri"] == ["https://api.test/calendar/callback"]
    assert calendar["include_granted_scopes"] == ["true"] and "include_granted_scopes" not in gmail
    for query in (gmail, postmaster, calendar):
        assert query["client_id"] == ["client-id"]
        assert (query["access_type"], query["prompt"], query["response_type"]) == (["offline"], ["consent"], ["code"])


@pytest.mark.usefixtures("google_settings")
def test_a_code_is_exchanged_with_the_redirect_address_of_its_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    forms: list[dict[str, list[str]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        forms.append(parse_qs(request.content.decode()))
        return httpx.Response(200, json={"access_token": "a", "refresh_token": "r", "expires_in": 3599})

    _serve_google(handler, monkeypatch)
    before = datetime.now(UTC).replace(tzinfo=None)
    gmail_tokens = asyncio.run(GmailOAuthService().exchange_code_for_tokens("code-1"))
    postmaster_tokens = asyncio.run(PostmasterOAuthService().exchange_code_for_tokens("code-2"))

    assert (gmail_tokens["access_token"], gmail_tokens["refresh_token"]) == ("a", "r")
    assert before + timedelta(seconds=3590) < gmail_tokens["expires_at"] < before + timedelta(seconds=3610)
    assert postmaster_tokens["refresh_token"] == "r"
    assert forms[0]["redirect_uri"] == ["https://api.test/gmail/callback"] and forms[0]["code"] == ["code-1"]
    assert forms[1]["redirect_uri"] == ["https://api.test/postmaster/callback"]
    assert all(form["client_secret"] == ["client-secret"] for form in forms)


@pytest.mark.usefixtures("google_settings")
def test_a_revoked_grant_is_an_access_to_reconnect_and_an_outage_is_not(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter([httpx.Response(400, json={"error": "invalid_grant"}), httpx.Response(503, text="down")])
    _serve_google(lambda request: next(answers), monkeypatch)

    with pytest.raises(GoogleOAuthError) as revoked:
        asyncio.run(GmailOAuthService().refresh_access_token("r"))
    with pytest.raises(GoogleOAuthError) as outage:
        asyncio.run(google_oauth_client.refresh("r", timeout_seconds=5))

    assert revoked.value.is_access_lost and str(revoked.value) == "Google a refusé l'accès (invalid_grant)"
    assert not outage.value.is_access_lost and outage.value.status_code == 503


@pytest.mark.usefixtures("google_settings")
def test_an_answer_without_an_access_token_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve_google(lambda request: httpx.Response(200, json={"refresh_token": "r"}), monkeypatch)

    with pytest.raises(GoogleOAuthError, match="sans jeton"):
        asyncio.run(PostmasterOAuthService().exchange_code_for_tokens("code"))


@pytest.mark.usefixtures("google_settings")
def test_the_account_profile_is_read_once_for_every_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    authorizations: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        authorizations.append(request.headers["authorization"])
        return httpx.Response(200, json={"email": "garage@gmail.com", "verified_email": True, "name": "Garage"})

    _serve_google(handler, monkeypatch)
    gmail = asyncio.run(GmailOAuthService().get_user_info("gmail-token"))
    postmaster = asyncio.run(PostmasterOAuthService().get_user_info("postmaster-token"))
    calendar_email = asyncio.run(GoogleCalendarClient().account_email("calendar-token"))

    assert gmail == {"email": "garage@gmail.com", "name": "Garage", "verified_email": True}
    assert postmaster["email"] == "garage@gmail.com" and postmaster["verified_email"] is True
    assert calendar_email == "garage@gmail.com"
    assert authorizations == ["Bearer gmail-token", "Bearer postmaster-token", "Bearer calendar-token"]
