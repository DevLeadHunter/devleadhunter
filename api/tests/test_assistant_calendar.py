"""
Booking in a sold assistant's Google agenda: the consent, the free slots, the booking, the visitor's messages.

Google is never called: the HTTP client is tested through an httpx MockTransport, everything else through a
fake client. The email sender, the SMS provider and the activity log are mocked; the database is an in-memory
SQLite. Routes are called directly. Business time is Paris (UTC+2 in September).
"""

import asyncio
import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import api.v1.routes.ai_assistant_client_space as client_routes
import api.v1.routes.ai_assistant_widget as routes
import migrations.add_ai_assistant_calendars_tables as calendars_migration
import services.ai_assistant.appointment_notices as notices_module
import services.ai_assistant.calendar_access as access_module
import services.ai_assistant.calendar_service as calendar_module
import services.ai_assistant.client_space_service as client_space_module
import services.ai_assistant.google_calendar_client as google_module
import services.email_sending_service as email_sending_module
import services.sms_service as sms_module
from enums.ai_assistant_request import AiAssistantRequestType
from enums.assistant_booking_mode import AssistantBookingMode
from enums.assistant_calendar_status import AssistantCalendarConnection, AssistantCalendarStatus
from enums.assistant_visitor_channel import AssistantVisitorChannel
from models.ai_assistant import AiAssistant
from models.ai_assistant_appointment import AiAssistantAppointment
from models.ai_assistant_calendar import AiAssistantCalendar
from models.ai_assistant_request import AiAssistantRequest
from models.prospect_db import ProspectDB
from models.sms_config import SmsConfig
from models.user import User
from schemas.ai_assistant import AiAssistantBookingChoice, AiAssistantLeadRequest
from schemas.ai_assistant_client_space import AiAssistantClientCalendarUpdate
from services.ai_assistant.appointment_notices import AppointmentTexts, BusinessCard, ai_assistant_appointment_notices
from services.ai_assistant.assistant_service import ai_assistant_service
from services.ai_assistant.calendar_booking import AiAssistantCalendarBooking, SlotTakenError
from services.ai_assistant.calendar_service import AiAssistantCalendarService, AiAssistantCalendarState
from services.ai_assistant.calendar_settings import CalendarSettings
from services.ai_assistant.calendar_slot_grid import AiAssistantCalendarSlotGrid
from services.ai_assistant.chat_service import AiAssistantChatService
from services.ai_assistant.client_links import AiAssistantClientLinks
from services.ai_assistant.google_calendar_client import (
    BusyPeriod,
    CalendarEventDraft,
    CalendarEventState,
    GoogleCalendarClient,
    GoogleCalendarError,
    GoogleTokens,
)
from services.ai_assistant.opening_hours import OpeningHoursCalendar
from services.ai_assistant.request_alerts import AlertSms
from services.ai_assistant.request_email import AiAssistantRequestEmail, RequestEmailContent
from services.encryption_service import encryption_service
from services.rate_limiter import SlidingWindowRateLimiter
from services.sms.gsm_segments import segment_count, to_gsm7
from tests.assistant_fakes import VISITOR_REQUEST, AcceptingSmsProvider, AsyncCallRecorder

_PARIS = ZoneInfo("Europe/Paris")
# Monday 21 September 2026, 10:00 in Paris (08:00 UTC).
_MONDAY_10H = datetime(2026, 9, 21, 10, 0, tzinfo=_PARIS)
_WEEK = [
    {"day": name, "hours": "08:00–12:00, 14:00–18:00"} for name in ("lundi", "mardi", "mercredi", "jeudi", "vendredi")
] + [{"day": "samedi", "hours": "Fermé"}, {"day": "dimanche", "hours": "Fermé"}]
_SCOPES = frozenset(
    {
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        google_module.GOOGLE_CALENDAR_EVENTS_SCOPE,
        google_module.GOOGLE_CALENDAR_FREEBUSY_SCOPE,
    }
)


def _paris(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, day, hour, minute, tzinfo=_PARIS)


def _utc(moment: datetime) -> datetime:
    return moment.astimezone(UTC).replace(tzinfo=None)


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    session = sessionmaker(bind=engine)()
    session.add(User(id=7, name="Dibodev", email="operateur@dibodev.fr", hashed_password="x"))
    session.commit()
    try:
        yield session
    finally:
        session.close()


class _FakeGoogle:
    """What Google answers: busy periods, created events, tokens."""

    def __init__(self) -> None:
        self.busy: list[BusyPeriod] = []
        self.busy_calls: list[tuple[datetime, datetime]] = []
        self.inserted: list[CalendarEventDraft] = []
        self.refreshed: list[str] = []
        self.failure: GoogleCalendarError | None = None
        # Failures answered to the next free/busy calls, one each, before the agenda answers normally.
        self.busy_failures: list[GoogleCalendarError] = []
        self.insert_failures: list[GoogleCalendarError] = []
        self.insert_calls = 0
        self.account = "garage.morel@gmail.com"
        self.scopes: frozenset[str] = _SCOPES
        # What ``get_event`` answers per event id; an inserted event not listed here still stands at its time.
        self.event_states: dict[str, CalendarEventState | None] = {}
        self.event_reads: list[str] = []

    async def busy_periods(self, access_token: str, calendar_id: str, *, start: datetime, end: datetime) -> list:
        if self.failure is not None:
            raise self.failure
        if self.busy_failures:
            raise self.busy_failures.pop(0)
        self.busy_calls.append((start, end))
        return list(self.busy)

    async def get_event(self, access_token: str, calendar_id: str, event_id: str) -> CalendarEventState | None:
        if self.failure is not None:
            raise self.failure
        self.event_reads.append(event_id)
        if event_id in self.event_states:
            return self.event_states[event_id]
        for draft in self.inserted:
            if draft.event_id == event_id:
                return CalendarEventState(cancelled=False, start=draft.start.astimezone(UTC).replace(tzinfo=None))
        return None

    async def insert_event(self, access_token: str, calendar_id: str, draft: CalendarEventDraft) -> str:
        self.insert_calls += 1
        if self.failure is not None:
            raise self.failure
        if self.insert_failures:
            raise self.insert_failures.pop(0)
        self.inserted.append(draft)
        return draft.event_id

    async def refresh(self, refresh_token: str) -> GoogleTokens:
        if self.failure is not None:
            raise self.failure
        self.refreshed.append(refresh_token)
        return GoogleTokens(
            access_token="fresh-access",
            refresh_token=refresh_token,
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
            scopes=self.scopes,
        )

    async def exchange_code(self, code: str) -> GoogleTokens:
        if code == "refused":
            raise GoogleCalendarError("Google a refusé l'accès (invalid_grant)")
        return GoogleTokens(
            access_token="access-1",
            refresh_token="refresh-1",
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
            scopes=self.scopes,
        )

    async def account_email(self, access_token: str) -> str | None:
        return self.account


@pytest.fixture
def google(monkeypatch: pytest.MonkeyPatch) -> _FakeGoogle:
    """A configured Google client that never leaves the process, and a quiet activity log."""
    fake = _FakeGoogle()
    for name in ("busy_periods", "insert_event", "get_event", "refresh", "exchange_code", "account_email"):
        monkeypatch.setattr(calendar_module.google_calendar_client, name, getattr(fake, name))
    monkeypatch.setattr(google_module.settings, "google_client_id", "client-id")
    monkeypatch.setattr(google_module.settings, "google_client_secret", "client-secret")
    monkeypatch.setattr(calendar_module.activity_log_service, "record", lambda **_: None)
    monkeypatch.setattr(notices_module.activity_log_service, "record", lambda **_: None)
    monkeypatch.setattr(client_space_module.activity_log_service, "record", lambda **_: None)
    return fake


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Mock the email sender and the SMS provider."""
    email = AsyncCallRecorder({"success": True})
    provider = AcceptingSmsProvider()
    monkeypatch.setattr(email_sending_module.EmailSendingService, "send_via_user_identity", email)
    monkeypatch.setattr(sms_module.notification_service, "notify_sms_event", AsyncCallRecorder())
    monkeypatch.setattr(sms_module.sms_service, "_provider", provider)
    return {"email": email, "sms": provider}


@pytest.fixture(autouse=True)
def fresh_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fresh rate limits and an empty free/busy cache for each test."""
    monkeypatch.setattr(client_routes, "assistant_client_limiter", SlidingWindowRateLimiter(120, 300))
    monkeypatch.setattr(routes, "assistant_chat_limiter", SlidingWindowRateLimiter(30, 300))
    monkeypatch.setattr(routes, "assistant_lead_limiter", SlidingWindowRateLimiter(8, 300))
    monkeypatch.setattr(access_module.ai_assistant_calendar_access, "_busy_cache", {})


def _assistant(db: Session, *, status: str = "delivered", hours: list[dict[str, str]] | None = _WEEK) -> AiAssistant:
    prospect = ProspectDB(name="Garage Morel", category="Garage", source="google", confidence=2, user_id=7)
    db.add(prospect)
    db.commit()
    assistant = ai_assistant_service.create(
        db, user_id=7, business_name="Garage Morel", prospect_id=prospect.id, country="FR", use_brand_color=False
    )
    assistant.knowledge_json = {
        **(assistant.knowledge_json or {}),
        "opening_hours": hours,
        "identity": {
            "business_name": "Garage Morel",
            "phone": "03 83 12 34 56",
            "address": "12 rue des Lilas, 54000 Nancy",
        },
    }
    assistant.status = status
    assistant.email = "contact@garage-morel.fr"
    if db.query(SmsConfig).filter(SmsConfig.user_id == 7).first() is None:
        db.add(SmsConfig(user_id=7, sender="Dibodev"))
    db.commit()
    return assistant


def _calendar(db: Session, assistant: AiAssistant, **fields: Any) -> AiAssistantCalendar:
    values: dict[str, Any] = {
        "user_id": assistant.user_id,
        "assistant_id": assistant.id,
        "account_email": "garage.morel@gmail.com",
        "access_token_encrypted": encryption_service.encrypt("access-0"),
        "refresh_token_encrypted": encryption_service.encrypt("refresh-0"),
        "token_expires_at": datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
        "status": AssistantCalendarStatus.CONNECTED.value,
    }
    values.update(fields)
    calendar = AiAssistantCalendar(**values)
    db.add(calendar)
    db.commit()
    return calendar


def _request(db: Session, assistant: AiAssistant, **fields: Any) -> AiAssistantRequest:
    values: dict[str, Any] = {
        "user_id": assistant.user_id,
        "prospect_id": assistant.prospect_id,
        "assistant_id": assistant.id,
        "name": "Julie Roux",
        "contact": "06 11 22 33 44",
        "need": "Vidange et plaquettes",
        "language": "fr",
        "session_id": "session-1",
    }
    values.update(fields)
    request = AiAssistantRequest(**values)
    db.add(request)
    db.commit()
    return request


def test_the_oauth_state_names_its_assistant_and_expires() -> None:
    now = datetime(2026, 9, 21, 8, 0)
    state = AiAssistantCalendarState.sign(42, now=now)

    assert AiAssistantCalendarState.read(state, now=now + timedelta(minutes=14)) == 42
    assert AiAssistantCalendarState.read(state, now=now + timedelta(minutes=16)) is None
    forged = state.replace("42.", "43.", 1)
    assert AiAssistantCalendarState.read(forged, now=now) is None
    assert AiAssistantCalendarState.read("42.1.abc", now=now) is None


def _client_with(handler: Any, monkeypatch: pytest.MonkeyPatch) -> GoogleCalendarClient:
    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def patched_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(google_module.httpx, "AsyncClient", patched_client)
    monkeypatch.setattr(google_module.settings, "google_client_id", "client-id")
    monkeypatch.setattr(google_module.settings, "google_client_secret", "client-secret")
    return GoogleCalendarClient()


def test_the_consent_url_asks_offline_access_to_the_events_and_the_availability() -> None:
    url = GoogleCalendarClient.authorization_url("7.123.sig")

    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "calendar.events" in url and "calendar.freebusy" in url
    assert "access_type=offline" in url and "prompt=consent" in url and "state=7.123.sig" in url


def test_the_client_reads_tokens_busy_periods_and_events(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "a",
                    "refresh_token": "r",
                    "expires_in": 3599,
                    "scope": " ".join(_SCOPES),
                },
            )
        if request.url.path == "/calendar/v3/freeBusy":
            return httpx.Response(
                200,
                json={
                    "calendars": {
                        "primary": {"busy": [{"start": "2026-09-22T12:00:00Z", "end": "2026-09-22T13:30:00Z"}]}
                    }
                },
            )
        return httpx.Response(200, json={"id": json.loads(request.content)["id"]})

    client = _client_with(handler, monkeypatch)
    tokens = asyncio.run(client.exchange_code("code"))
    busy = asyncio.run(
        client.busy_periods("a", "primary", start=datetime(2026, 9, 22, 0, 0), end=datetime(2026, 9, 23, 0, 0))
    )
    draft = CalendarEventDraft(
        event_id="dlh1abc",
        summary="Révision — Julie Roux",
        description="Contact : 06",
        start=_paris(22, 10),
        end=_paris(22, 11),
        time_zone="Europe/Paris",
        request_id=5,
    )
    event_id = asyncio.run(client.insert_event("a", "agenda du garage@group.calendar.google.com", draft))

    assert (tokens.access_token, tokens.refresh_token) == ("a", "r")
    assert tokens.scopes >= _SCOPES
    assert busy == [BusyPeriod(start=datetime(2026, 9, 22, 12, 0), end=datetime(2026, 9, 22, 13, 30))]
    assert json.loads(seen[1].content)["timeMin"] == "2026-09-22T00:00:00Z"
    assert event_id == "dlh1abc"
    body = json.loads(seen[2].content)
    assert body["start"] == {"dateTime": "2026-09-22T10:00:00+02:00", "timeZone": "Europe/Paris"}
    assert "agenda%20du%20garage%40group.calendar.google.com" in str(seen[2].url)


def test_the_client_tells_a_lost_access_from_a_passing_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter(
        [
            httpx.Response(400, json={"error": "invalid_grant"}),
            httpx.Response(401, json={"error": {"message": "Invalid Credentials"}}),
            httpx.Response(403, json={"error": {"errors": [{"reason": "rateLimitExceeded"}]}}),
            httpx.Response(409, json={"error": {"errors": [{"reason": "duplicate"}]}}),
            httpx.Response(200, json={"calendars": {"primary": {"errors": [{"reason": "notFound"}]}}}),
        ]
    )
    client = _client_with(lambda request: next(answers), monkeypatch)
    window = {"start": datetime(2026, 9, 22), "end": datetime(2026, 9, 23)}
    draft = CalendarEventDraft(
        event_id="dlh2",
        summary="s",
        description="d",
        start=_paris(22, 10),
        end=_paris(22, 11),
        time_zone="UTC",
        request_id=1,
    )

    with pytest.raises(GoogleCalendarError) as revoked:
        asyncio.run(client.refresh("r"))
    with pytest.raises(GoogleCalendarError) as unauthorized:
        asyncio.run(client.busy_periods("a", "primary", **window))
    with pytest.raises(GoogleCalendarError) as limited:
        asyncio.run(client.busy_periods("a", "primary", **window))
    duplicate = asyncio.run(client.insert_event("a", "primary", draft))
    with pytest.raises(GoogleCalendarError) as missing:
        asyncio.run(client.busy_periods("a", "primary", **window))

    assert revoked.value.needs_reconnect and unauthorized.value.needs_reconnect
    assert not limited.value.needs_reconnect
    assert duplicate == "dlh2"
    assert "notFound" in str(missing.value)


def test_the_consent_stores_encrypted_tokens_on_a_sold_assistant_only(db: Session, google: _FakeGoogle) -> None:
    assistant = _assistant(db)
    demo = _assistant(db, status="active")
    service = AiAssistantCalendarService()

    connected_assistant, calendar = asyncio.run(
        service.connect(db, code="ok", state=AiAssistantCalendarState.sign(assistant.id))
    )

    assert connected_assistant.id == assistant.id
    assert calendar.account_email == "garage.morel@gmail.com"
    assert calendar.status == AssistantCalendarStatus.CONNECTED.value
    assert calendar.refresh_token_encrypted and "refresh-1" not in calendar.refresh_token_encrypted
    assert encryption_service.decrypt(calendar.refresh_token_encrypted) == "refresh-1"
    with pytest.raises(ValueError, match="ne peut pas recevoir"):
        asyncio.run(service.connect(db, code="ok", state=AiAssistantCalendarState.sign(demo.id)))
    with pytest.raises(ValueError, match="expiré"):
        asyncio.run(service.connect(db, code="ok", state="1.1.AAAAAAAAAAAAAAAAAAAAAA"))
    with pytest.raises(GoogleCalendarError):
        asyncio.run(service.connect(db, code="refused", state=AiAssistantCalendarState.sign(assistant.id)))


def test_a_consent_without_both_agenda_permissions_stores_nothing(db: Session, google: _FakeGoogle) -> None:
    assistant = _assistant(db)
    google.scopes = frozenset({"openid", google_module.GOOGLE_CALENDAR_EVENTS_SCOPE})

    with pytest.raises(ValueError, match="deux accès"):
        asyncio.run(
            AiAssistantCalendarService().connect(db, code="ok", state=AiAssistantCalendarState.sign(assistant.id))
        )

    assert db.query(AiAssistantCalendar).count() == 0


def test_the_offer_leaves_out_slots_already_booked_here(db: Session, google: _FakeGoogle) -> None:
    assistant = _assistant(db)
    calendar = _calendar(db, assistant)
    request = _request(db, assistant)
    db.add(
        AiAssistantAppointment(
            user_id=7,
            assistant_id=assistant.id,
            request_id=request.id,
            starts_at=_utc(_paris(22, 10)),
            ends_at=_utc(_paris(22, 11)),
            google_event_id="dlhbooked",
        )
    )
    db.commit()

    page = asyncio.run(AiAssistantCalendarService().free_slots(db, assistant, calendar, now=_MONDAY_10H))

    assert page.slots[0].start == _paris(22, 11)


def test_an_expired_access_token_is_refreshed_and_stored_encrypted(db: Session, google: _FakeGoogle) -> None:
    assistant = _assistant(db)
    calendar = _calendar(db, assistant, token_expires_at=datetime(2026, 1, 1))

    asyncio.run(AiAssistantCalendarService().free_slots(db, assistant, calendar, now=_MONDAY_10H))
    db.rollback()

    assert google.refreshed == ["refresh-0"]
    db.refresh(calendar)
    assert encryption_service.decrypt(calendar.access_token_encrypted) == "fresh-access"


def _settings(**overrides: Any) -> CalendarSettings:
    values: dict[str, Any] = {
        "calendar_id": "primary",
        "duration_minutes": 60,
        "min_notice_hours": 24,
        "appointment_types": (),
    }
    values.update(overrides)
    return CalendarSettings(**values)


def _starts(page: Any) -> list[datetime]:
    return [slot.start for slot in page.slots]


def test_the_first_free_slot_of_each_half_day_after_the_notice_and_within_the_hours() -> None:
    busy = [BusyPeriod(start=_utc(_paris(22, 14)), end=_utc(_paris(22, 15, 30)))]

    page = AiAssistantCalendarSlotGrid.compute_slots(
        opening_hours=_WEEK, busy=busy, settings=_settings(), now=_MONDAY_10H, after=None, count=3
    )

    assert _starts(page) == [_paris(22, 10), _paris(22, 15, 30), _paris(23, 8)]
    assert page.has_more
    assert page.slots[0].end == _paris(22, 11)


def test_the_next_page_starts_at_the_half_day_after_the_last_slot_shown() -> None:
    page = AiAssistantCalendarSlotGrid.compute_slots(
        opening_hours=_WEEK, busy=[], settings=_settings(), now=_MONDAY_10H, after=_paris(23, 8), count=3
    )

    assert _starts(page) == [_paris(23, 14), _paris(24, 8), _paris(24, 14)]


def test_a_slot_never_runs_over_a_closing_time_nor_into_the_weekend() -> None:
    friday_afternoon = datetime(2026, 9, 25, 16, 45, tzinfo=_PARIS)

    page = AiAssistantCalendarSlotGrid.compute_slots(
        opening_hours=_WEEK,
        busy=[],
        settings=_settings(duration_minutes=90, min_notice_hours=0),
        now=friday_afternoon,
        after=None,
        count=2,
    )

    # 17:00-18:30 would run past 18:00; Saturday and Sunday are closed.
    assert _starts(page) == [_paris(28, 8), _paris(28, 14)]


def test_unknown_hours_offer_the_weekday_office_hours() -> None:
    page = AiAssistantCalendarSlotGrid.compute_slots(
        opening_hours=None, busy=[], settings=_settings(min_notice_hours=0), now=_MONDAY_10H, after=None, count=3
    )

    assert _starts(page) == [_paris(21, 10), _paris(21, 14), _paris(22, 9)]


def test_a_booking_creates_the_event_and_the_appointment(db: Session, google: _FakeGoogle) -> None:
    assistant = _assistant(db)
    calendar = _calendar(db, assistant, appointment_types_json=["Révision", "Contrôle technique"])
    request = _request(db, assistant)

    appointment = asyncio.run(
        AiAssistantCalendarBooking().book(
            db,
            assistant,
            calendar,
            request,
            start=_paris(24, 14),
            type_label="révision",
            visitor_phone_e164="+33611223344",
            visitor_email=None,
            now=_MONDAY_10H,
        )
    )

    [draft] = google.inserted
    assert appointment.google_event_id == draft.event_id and draft.event_id.startswith("dlh")
    assert (appointment.starts_at, appointment.ends_at) == (_utc(_paris(24, 14)), _utc(_paris(24, 15)))
    assert appointment.type_label == "Révision"
    assert draft.summary == "Révision — Julie Roux"
    assert "Contact : 06 11 22 33 44" in draft.description and "Vidange et plaquettes" in draft.description
    # The reminder leaves the day before at the same time (business hours).
    assert appointment.reminder_due_at == _utc(_paris(23, 14))
    assert google.busy_calls == [(_utc(_paris(24, 14)), _utc(_paris(24, 15)))]


def test_a_booking_checks_the_slot_and_the_kind_again(db: Session, google: _FakeGoogle) -> None:
    assistant = _assistant(db)
    calendar = _calendar(db, assistant, appointment_types_json=["Révision"])
    request = _request(db, assistant)
    service = AiAssistantCalendarBooking()

    def book(start: datetime, type_label: str | None = "Révision") -> AiAssistantAppointment:
        return asyncio.run(
            service.book(
                db,
                assistant,
                calendar,
                request,
                start=start,
                type_label=type_label,
                visitor_phone_e164=None,
                visitor_email=None,
                now=_MONDAY_10H,
            )
        )

    for refused in (_paris(22, 10, 10), _paris(21, 15), _paris(26, 10), _paris(22, 12, 30)):
        with pytest.raises(ValueError, match="plus proposé"):
            book(refused)
    with pytest.raises(ValueError, match="type de rendez-vous"):
        book(_paris(22, 10), None)
    google.busy = [BusyPeriod(start=_utc(_paris(22, 10, 30)), end=_utc(_paris(22, 11)))]
    with pytest.raises(SlotTakenError):
        book(_paris(22, 10))
    assert db.query(AiAssistantAppointment).count() == 0
    assert google.inserted == []


def test_one_request_books_one_appointment_and_two_visitors_never_share_a_slot(
    db: Session, google: _FakeGoogle
) -> None:
    assistant = _assistant(db)
    calendar = _calendar(db, assistant)
    first_request = _request(db, assistant)
    second_request = _request(db, assistant, session_id="session-2", name="Marc Petit")
    service = AiAssistantCalendarBooking()

    def book(request: AiAssistantRequest, start: datetime) -> AiAssistantAppointment:
        return asyncio.run(
            service.book(
                db,
                assistant,
                calendar,
                request,
                start=start,
                type_label=None,
                visitor_phone_e164=None,
                visitor_email=None,
                now=_MONDAY_10H,
            )
        )

    booked = book(first_request, _paris(22, 10))
    again = book(first_request, _paris(23, 10))

    assert again.id == booked.id
    assert len(google.inserted) == 1
    # Google does not show it yet: the booking is still refused from the local rows.
    with pytest.raises(SlotTakenError):
        book(second_request, _paris(22, 10, 30) - timedelta(minutes=30))


def test_a_booking_the_agenda_refuses_falls_back_on_the_half_day_and_flags_the_agenda(
    db: Session, google: _FakeGoogle
) -> None:
    assistant = _assistant(db)
    calendar = _calendar(db, assistant)
    request = _request(db, assistant)
    google.failure = GoogleCalendarError("Google Agenda a refusé l'appel (401)", needs_reconnect=True, status_code=401)

    outcome = asyncio.run(
        AiAssistantCalendarBooking().book_request(
            db, assistant, request, start=_paris(24, 14), type_label=None, now=_MONDAY_10H
        )
    )

    assert outcome.appointment is None
    assert request.type == AiAssistantRequestType.APPOINTMENT.value
    assert request.appointment_slots_json == [{"date": "2026-09-24", "period": "afternoon"}]
    db.refresh(calendar)
    assert calendar.status == AssistantCalendarStatus.ERROR.value
    assert access_module.ai_assistant_calendar_access.usable_calendar(db, assistant) is None


def test_the_reminder_leaves_the_day_before_within_the_day_or_not_at_all() -> None:
    booked_monday = _utc(_MONDAY_10H)

    assert AiAssistantCalendarBooking.reminder_due_at(_utc(_paris(24, 8)), booked_at=booked_monday) == _utc(
        _paris(23, 9)
    )
    assert AiAssistantCalendarBooking.reminder_due_at(_utc(_paris(24, 21)), booked_at=booked_monday) == _utc(
        _paris(23, 19)
    )
    assert AiAssistantCalendarBooking.reminder_due_at(_utc(_paris(22, 11)), booked_at=booked_monday) is None


def test_the_visitor_is_told_on_the_channel_they_left(db: Session, google: _FakeGoogle) -> None:
    assistant = _assistant(db)
    service = AiAssistantCalendarBooking()

    assert service.visitor_channels(db, assistant, " 06 11 22 33 44 ") == ("+33611223344", None)
    assert service.visitor_channels(db, assistant, "Julie.Roux@Example.fr") == (None, "julie.roux@example.fr")
    assert service.visitor_channels(db, assistant, "03 83 12 34 56") == (None, None)


def test_the_confirmation_and_the_reminder_fit_one_sms_in_every_language() -> None:
    card = BusinessCard(
        name="Garage Morel & Fils Carrosserie",
        phone="+33 3 83 12 34 56",
        email=None,
        address="12 rue des Lilas, 54000 Nancy",
    )
    for language in AppointmentTexts.LANGUAGES:
        confirmation = AppointmentTexts.confirmation_sms(
            card=card, start_local=_paris(24, 14), type_label="Contrôle technique complet", language=language
        )
        reminder = AppointmentTexts.reminder_sms(card=card, start_local=_paris(24, 14), language=language)

        assert segment_count(to_gsm7(confirmation)) == 1
        assert segment_count(to_gsm7(reminder)) == 1
        assert "14:00" in confirmation and "14:00" in reminder

    assert AppointmentTexts.confirmation_sms(
        card=card, start_local=_paris(24, 14), type_label="Révision", language="fr"
    ) == (
        "Garage Morel & Fils Carrosserie : votre rendez-vous du jeu. 24/09 à 14:00 (Révision) est confirmé. "
        "Empeché ? Appelez le +33 3 83 12 34 56."
    )
    assert "Ihr Termin am Do. 24.09. um 14:00" in AppointmentTexts.confirmation_sms(
        card=card, start_local=_paris(24, 14), type_label=None, language="de"
    )
    assert AppointmentTexts.language("lu") == "fr"


def test_a_business_name_outside_gsm7_never_costs_the_visitor_their_sms() -> None:
    card = BusinessCard(name="Garage Auto Service N°1 🚗", phone="03 83 12 34 56", email=None, address="1 rue Haute")

    confirmation = AppointmentTexts.confirmation_sms(
        card=card, start_local=_paris(24, 14), type_label="Révision", language="fr"
    )
    reminder = AppointmentTexts.reminder_sms(card=card, start_local=_paris(24, 14), language="fr")

    for text in (confirmation, reminder):
        assert segment_count(text) == 1
        assert "Garage Auto Service N1" in text and "°" not in text and "🚗" not in text
    assert "(Révision)" in confirmation and "03 83 12 34 56" in reminder


def test_the_confirmation_email_never_asks_to_reply_and_carries_the_ics(
    db: Session, google: _FakeGoogle, outbox: dict[str, Any]
) -> None:
    assistant = _assistant(db)
    request = _request(db, assistant, contact="julie@example.fr", language="en")
    appointment = AiAssistantAppointment(
        user_id=7,
        assistant_id=assistant.id,
        request_id=request.id,
        starts_at=_utc(_paris(24, 14)),
        ends_at=_utc(_paris(24, 15)),
        type_label="Révision",
        google_event_id="dlh1abcd",
        visitor_email="julie@example.fr",
        language="en",
    )
    db.add(appointment)
    db.commit()

    assert asyncio.run(ai_assistant_appointment_notices.send_confirmation(db, appointment))
    assert not asyncio.run(ai_assistant_appointment_notices.send_confirmation(db, appointment))

    [sent] = outbox["email"].calls
    assert sent["recipient_email"] == "julie@example.fr"
    assert sent["subject"] == "Your appointment at Garage Morel: Thursday 24 September at 14:00"
    assert "please do not reply" in sent["body_html"]
    assert "03 83 12 34 56" in sent["body_html"]
    [attachment] = sent["attachments"]
    ics = attachment.content.decode()
    assert attachment.content_type == "text/calendar"
    assert "DTSTART:20260924T120000Z" in ics and "DTEND:20260924T130000Z" in ics
    assert "LOCATION:12 rue des Lilas\\, 54000 Nancy" in ics
    assert outbox["sms"].texts == []


def test_the_runner_sends_due_reminders_once_and_skips_late_ones(
    db: Session, google: _FakeGoogle, outbox: dict[str, Any]
) -> None:
    assistant = _assistant(db)
    now = _utc(_paris(23, 14, 5))

    def appointment(start: datetime, due: datetime, **fields: Any) -> AiAssistantAppointment:
        # One request per appointment: the table allows no second appointment on a request.
        request = _request(db, assistant, session_id=f"session-{start.day}-{start.hour}")
        row = AiAssistantAppointment(
            user_id=7,
            assistant_id=assistant.id,
            request_id=request.id,
            starts_at=_utc(start),
            ends_at=_utc(start + timedelta(hours=1)),
            google_event_id=f"dlh{start.day}{start.hour}",
            visitor_phone_e164="+33611223344",
            language="fr",
            confirmation_sent_at=datetime(2026, 9, 21, 8, 0),
            reminder_due_at=_utc(due),
            created_at=datetime(2026, 9, 21, 8, 0),
            **fields,
        )
        db.add(row)
        db.commit()
        return row

    due = appointment(_paris(24, 14), _paris(23, 14))
    appointment(_paris(23, 14, 30), _paris(22, 14, 30))
    appointment(_paris(25, 14), _paris(24, 14))

    assert asyncio.run(ai_assistant_appointment_notices.run_pass(db, now=now)) == 1
    assert asyncio.run(ai_assistant_appointment_notices.run_pass(db, now=now)) == 0

    [sms] = outbox["sms"].texts
    assert sms.startswith("Rappel : rendez-vous demain, 14:00, chez Garage Morel.")
    db.refresh(due)
    assert due.reminder_sent_at is not None


def test_a_token_google_dropped_early_is_refreshed_once_before_the_agenda_is_declared_lost(
    db: Session, google: _FakeGoogle
) -> None:
    assistant = _assistant(db)
    calendar = _calendar(db, assistant)
    google.busy_failures = [
        GoogleCalendarError("Google Agenda a refusé l'appel (401)", needs_reconnect=True, status_code=401)
    ]

    slots = asyncio.run(
        calendar_module.ai_assistant_calendar_service.free_slots(db, assistant, calendar, now=_MONDAY_10H)
    )

    db.refresh(calendar)
    assert slots.slots and google.refreshed == ["refresh-0"]
    assert calendar.status == AssistantCalendarStatus.CONNECTED.value and calendar.last_error is None


def test_a_reminder_follows_what_the_agenda_says_of_the_event(
    db: Session, google: _FakeGoogle, outbox: dict[str, Any]
) -> None:
    assistant = _assistant(db)
    _calendar(db, assistant)
    now = _utc(_paris(23, 14, 5))

    def appointment(start: datetime, due: datetime, event_id: str) -> AiAssistantAppointment:
        request = _request(db, assistant, session_id=f"session-{event_id}")
        row = AiAssistantAppointment(
            user_id=7,
            assistant_id=assistant.id,
            request_id=request.id,
            starts_at=_utc(start),
            ends_at=_utc(start + timedelta(hours=1)),
            google_event_id=event_id,
            visitor_phone_e164="+33611223344",
            language="fr",
            confirmation_sent_at=datetime(2026, 9, 21, 8, 0),
            reminder_due_at=_utc(due),
            created_at=datetime(2026, 9, 21, 8, 0),
        )
        db.add(row)
        db.commit()
        return row

    appointment(_paris(24, 14), _paris(23, 14), "dlh-cancelled")
    moved = appointment(_paris(24, 10), _paris(23, 10), "dlh-moved")
    appointment(_paris(24, 11), _paris(23, 11), "dlh-deleted")
    appointment(_paris(24, 12), _paris(23, 12), "dlh-postponed")
    google.event_states["dlh-cancelled"] = CalendarEventState(cancelled=True, start=None)
    google.event_states["dlh-moved"] = CalendarEventState(cancelled=False, start=_utc(_paris(24, 16, 30)))
    google.event_states["dlh-deleted"] = None
    google.event_states["dlh-postponed"] = CalendarEventState(cancelled=False, start=_utc(_paris(28, 12)))

    # Every reminder is claimed; only the one still tomorrow leaves, at the time the agenda now holds.
    assert asyncio.run(ai_assistant_appointment_notices.run_pass(db, now=now)) == 4
    [sms] = outbox["sms"].texts
    assert sms.startswith("Rappel : rendez-vous demain, 16:30, chez Garage Morel.")
    db.refresh(moved)
    assert (moved.starts_at, moved.ends_at) == (_utc(_paris(24, 16, 30)), _utc(_paris(24, 17, 30)))
    assert sorted(google.event_reads) == ["dlh-cancelled", "dlh-deleted", "dlh-moved", "dlh-postponed"]
    assert asyncio.run(ai_assistant_appointment_notices.run_pass(db, now=now)) == 0


def test_a_confirmation_lost_by_a_restart_is_sent_by_the_runner(
    db: Session, google: _FakeGoogle, outbox: dict[str, Any]
) -> None:
    assistant = _assistant(db)
    request = _request(db, assistant)
    lost = AiAssistantAppointment(
        user_id=7,
        assistant_id=assistant.id,
        request_id=request.id,
        starts_at=_utc(_paris(24, 14)),
        ends_at=_utc(_paris(24, 15)),
        google_event_id="dlhlost",
        visitor_phone_e164="+33611223344",
        language="fr",
        created_at=_utc(_MONDAY_10H),
    )
    db.add(lost)
    db.commit()

    assert asyncio.run(ai_assistant_appointment_notices.run_pass(db, now=_utc(_MONDAY_10H) + timedelta(minutes=1))) == 0
    assert asyncio.run(ai_assistant_appointment_notices.run_pass(db, now=_utc(_MONDAY_10H) + timedelta(minutes=5))) == 1

    [sms] = outbox["sms"].texts
    assert "votre rendez-vous du jeu. 24/09 à 14:00 est confirmé" in sms


@pytest.fixture
def business_clock(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Monday 10:00 in Paris, and the background work recorded instead of run."""
    scheduled: list[int] = []
    monkeypatch.setattr(OpeningHoursCalendar, "business_now", staticmethod(lambda: _MONDAY_10H))
    monkeypatch.setattr(routes.ai_assistant_request_service, "schedule_follow_up", lambda request_id: None)
    monkeypatch.setattr(routes.ai_assistant_appointment_notices, "schedule_confirmation", scheduled.append)
    return scheduled


def test_the_slots_route_offers_the_agenda_or_falls_back_on_half_days(
    db: Session, google: _FakeGoogle, business_clock: list[int]
) -> None:
    assistant = _assistant(db)
    _calendar(db, assistant, appointment_types_json=["Révision"], duration_minutes=30)

    offer = asyncio.run(routes.get_assistant_appointment_slots(assistant.slug, VISITOR_REQUEST, after=None, db=db))
    google.failure = GoogleCalendarError("Google Agenda injoignable")
    access_module.ai_assistant_calendar_access._busy_cache.clear()
    fallback = asyncio.run(routes.get_assistant_appointment_slots(assistant.slug, VISITOR_REQUEST, after=None, db=db))

    assert offer.mode is AssistantBookingMode.CALENDAR
    assert [time.start for time in offer.times] == [_paris(22, 10), _paris(22, 14), _paris(23, 8)]
    assert (offer.types, offer.duration_minutes, offer.max_chosen, offer.has_more) == (["Révision"], 30, 1, True)
    assert fallback.mode is AssistantBookingMode.REQUEST
    assert fallback.times == [] and fallback.days


def test_the_lead_route_books_the_slot_or_answers_409_when_it_was_taken(
    db: Session, google: _FakeGoogle, business_clock: list[int]
) -> None:
    assistant = _assistant(db)
    _calendar(db, assistant)
    payload = AiAssistantLeadRequest(
        name="Julie Roux",
        contact="06 11 22 33 44",
        session_id="session-1",
        booking=AiAssistantBookingChoice(start=_paris(22, 10)),
    )

    answer = asyncio.run(routes.submit_assistant_lead(assistant.slug, payload, VISITOR_REQUEST, db))

    assert answer.booked_start == _paris(22, 10)
    [appointment] = db.query(AiAssistantAppointment).all()
    assert business_clock == [appointment.id]
    assert appointment.visitor_phone_e164 == "+33611223344"
    taken = payload.model_copy(update={"session_id": "session-2", "name": "Marc Petit"})
    with pytest.raises(HTTPException) as refused:
        asyncio.run(routes.submit_assistant_lead(assistant.slug, taken, VISITOR_REQUEST, db))
    assert refused.value.status_code == 409


def test_the_chat_opens_the_appointment_panel_when_the_visitor_asks_for_one() -> None:
    asks = AiAssistantChatService.asks_for_appointment

    for message in (
        "Je voudrais prendre rendez-vous mardi",
        "Avez-vous un créneau demain ?",
        "Ik wil een afspraak maken",
        "Ich möchte einen Termin vereinbaren",
        "Can I book an appointment?",
        "Un RDV pour une vidange svp",
    ):
        assert asks(message), message
    for message in ("Le chantier est terminé ?", "Quels sont vos tarifs ?", "Merci beaucoup"):
        assert not asks(message), message


def test_the_client_space_shows_the_agenda_and_the_upcoming_appointments(
    db: Session, google: _FakeGoogle, monkeypatch: pytest.MonkeyPatch
) -> None:
    assistant = _assistant(db)
    token = AiAssistantClientLinks.token(assistant.id)
    disconnected = asyncio.run(client_routes.get_client_space(token, VISITOR_REQUEST, db))
    _calendar(db, assistant, appointment_types_json=["Révision"])
    request = _request(db, assistant)
    start = datetime.now(UTC).replace(tzinfo=None, microsecond=0) + timedelta(days=2)
    db.add(
        AiAssistantAppointment(
            user_id=7,
            assistant_id=assistant.id,
            request_id=request.id,
            starts_at=start,
            ends_at=start + timedelta(hours=1),
            type_label="Révision",
            google_event_id="dlhspace",
        )
    )
    db.commit()

    space = asyncio.run(client_routes.get_client_space(token, VISITOR_REQUEST, db))
    monkeypatch.setattr(google_module.settings, "google_client_id", "")
    unavailable = asyncio.run(client_routes.get_client_space(token, VISITOR_REQUEST, db))

    assert disconnected.calendar.status is AssistantCalendarConnection.DISCONNECTED
    assert space.calendar.status is AssistantCalendarConnection.CONNECTED
    assert space.calendar.account_email == "garage.morel@gmail.com"
    assert (space.calendar.duration_minutes, space.calendar.min_notice_hours) == (60, 24)
    assert space.calendar.appointment_types == ["Révision"]
    [upcoming] = space.appointments
    assert (upcoming.name, upcoming.type_label) == ("Julie Roux", "Révision")
    assert space.requests[0].appointment_booked.endswith("(Révision)")
    assert unavailable.calendar.status is AssistantCalendarConnection.UNAVAILABLE


def test_the_client_connects_changes_and_disconnects_the_agenda(
    db: Session, google: _FakeGoogle, outbox: dict[str, Any]
) -> None:
    assistant = _assistant(db)
    token = AiAssistantClientLinks.token(assistant.id)

    consent = asyncio.run(client_routes.connect_client_calendar(token, VISITOR_REQUEST, db))
    state = consent.url.split("state=")[1]
    page = asyncio.run(client_routes.google_calendar_callback(VISITOR_REQUEST, code="ok", state=state, error="", db=db))
    settings = asyncio.run(
        client_routes.update_client_calendar(
            token,
            AiAssistantClientCalendarUpdate(
                duration_minutes=30, min_notice_hours=4, appointment_types=[" Révision ", "révision", "Pneus"]
            ),
            VISITOR_REQUEST,
            db,
        )
    )
    with pytest.raises(HTTPException) as refused:
        asyncio.run(
            client_routes.update_client_calendar(
                token, AiAssistantClientCalendarUpdate(duration_minutes=50), VISITOR_REQUEST, db
            )
        )
    disconnected = asyncio.run(client_routes.disconnect_client_calendar(token, VISITOR_REQUEST, db))

    assert "Google Agenda est connecté" in page.body.decode()
    assert page.headers["referrer-policy"] == "no-referrer"
    [notice] = outbox["email"].calls
    assert notice["subject"] == "Votre agenda Google est connecté"
    assert "garage.morel@gmail.com" in notice["body_html"]
    assert (settings.duration_minutes, settings.min_notice_hours) == (30, 4)
    assert settings.appointment_types == ["Révision", "Pneus"]
    assert refused.value.status_code == 422
    assert disconnected.status is AssistantCalendarConnection.DISCONNECTED
    assert db.query(AiAssistantCalendar).count() == 0


def test_the_callback_page_explains_a_failed_consent(db: Session, google: _FakeGoogle) -> None:
    denied = asyncio.run(
        client_routes.google_calendar_callback(VISITOR_REQUEST, code="", state="", error="access_denied", db=db)
    )
    forged = asyncio.run(
        client_routes.google_calendar_callback(
            VISITOR_REQUEST, code="ok", state="9.9.AAAAAAAAAAAAAAAAAAAAAA", error="", db=db
        )
    )

    assert "Connexion annulée" in denied.body.decode()
    assert "Lien de connexion expiré" in forged.body.decode()
    assert db.query(AiAssistantCalendar).count() == 0


def test_the_owner_is_told_the_appointment_is_already_in_the_agenda() -> None:
    sms = AlertSms.new_request(
        request_type=AiAssistantRequestType.APPOINTMENT,
        name="Julie Roux",
        contact="06 11 22 33 44",
        summary="Vidange et plaquettes avant, elle passe avec la voiture de sa fille.",
        has_photos=False,
        link="demo.dibodev.fr/client/1234.tneuo0.K4lzdHZLLanlAxWK",
        booked="jeu. 24/09 à 14:00 (Révision)",
    )
    email = AiAssistantRequestEmail.render(
        RequestEmailContent(
            business_name="Garage Morel",
            assistant_name="Léa",
            request_type=AiAssistantRequestType.APPOINTMENT,
            visitor_name="Julie Roux",
            contact="06 11 22 33 44",
            need=None,
            need_summary="Vidange.",
            received_at=datetime(2026, 9, 21, 10, 0),
            received_outside_hours=False,
            transcript=[],
            handled_url="https://api.example.fr/handled",
            appointment_booked="jeu. 24/09 à 14:00 (Révision)",
        )
    )

    assert sms.startswith("RDV réservé le jeu. 24/09 à 14:00 (Révision) par Julie Roux, 06 11 22 33 44 : Vidange")
    assert segment_count(sms) == 1
    assert email.subject == "Rendez-vous réservé — Julie Roux"
    assert "Dans votre agenda" in email.html


def test_the_migration_creates_both_tables_once(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    monkeypatch.setattr(calendars_migration, "engine", engine)

    calendars_migration.run_migration()
    calendars_migration.run_migration()

    tables = set(inspect(engine).get_table_names())
    assert {"ai_assistant_calendars", "ai_assistant_appointments"} <= tables


def _book(
    db: Session, assistant: AiAssistant, calendar: AiAssistantCalendar, request: AiAssistantRequest, start: datetime
) -> AiAssistantAppointment:
    return asyncio.run(
        AiAssistantCalendarBooking().book(
            db,
            assistant,
            calendar,
            request,
            start=start,
            type_label=None,
            visitor_phone_e164=None,
            visitor_email=None,
            now=_MONDAY_10H,
        )
    )


def test_a_lost_insert_answer_is_retried_with_the_same_event_id(db: Session, google: _FakeGoogle) -> None:
    assistant = _assistant(db)
    calendar = _calendar(db, assistant)
    request = _request(db, assistant)
    google.insert_failures = [GoogleCalendarError("Google Agenda injoignable")]

    appointment = _book(db, assistant, calendar, request, _paris(22, 10))

    assert google.insert_calls == 2
    assert appointment.google_event_id == AiAssistantCalendarBooking._event_id(request.id, _utc(_paris(22, 10)))
    assert db.query(AiAssistantAppointment).count() == 1


def test_a_taken_slot_empties_the_free_busy_cache(db: Session, google: _FakeGoogle) -> None:
    assistant = _assistant(db)
    calendar = _calendar(db, assistant)
    access = access_module.ai_assistant_calendar_access
    asyncio.run(calendar_module.ai_assistant_calendar_service.free_slots(db, assistant, calendar, now=_MONDAY_10H))
    assert calendar.id in access._busy_cache
    google.busy = [BusyPeriod(start=_utc(_paris(22, 10)), end=_utc(_paris(22, 11)))]

    with pytest.raises(SlotTakenError):
        asyncio.run(
            AiAssistantCalendarBooking().book(
                db,
                assistant,
                calendar,
                _request(db, assistant),
                start=_paris(22, 10),
                type_label=None,
                visitor_phone_e164=None,
                visitor_email=None,
                now=_MONDAY_10H,
            )
        )

    assert calendar.id not in access._busy_cache


def test_a_refused_insert_is_kept_as_the_agendas_last_problem(db: Session, google: _FakeGoogle) -> None:
    assistant = _assistant(db)
    calendar = _calendar(db, assistant)
    google.insert_failures = [GoogleCalendarError("Google Agenda a refusé l'appel (403)", status_code=403)]

    with pytest.raises(GoogleCalendarError):
        _book(db, assistant, calendar, _request(db, assistant), _paris(22, 10))

    db.refresh(calendar)
    assert calendar.status == AssistantCalendarStatus.CONNECTED.value
    assert "lecture seule" in calendar.last_error
    appointment = _book(db, assistant, calendar, _request(db, assistant, session_id="session-2"), _paris(22, 14))
    db.refresh(calendar)
    assert appointment.google_event_id and calendar.last_error is None


def test_a_day_of_bookings_is_capped_and_the_rest_become_wishes(
    db: Session, google: _FakeGoogle, monkeypatch: pytest.MonkeyPatch
) -> None:
    assistant = _assistant(db)
    _calendar(db, assistant)
    monkeypatch.setattr(AiAssistantCalendarBooking, "MAX_BOOKINGS_PER_DAY", 1)
    service = AiAssistantCalendarBooking()

    first = asyncio.run(
        service.book_request(
            db, assistant, _request(db, assistant), start=_paris(22, 10), type_label=None, now=_MONDAY_10H
        )
    )
    capped_request = _request(db, assistant, session_id="session-2")
    second = asyncio.run(
        service.book_request(db, assistant, capped_request, start=_paris(22, 14), type_label=None, now=_MONDAY_10H)
    )

    assert first.appointment is not None and second.appointment is None
    assert capped_request.appointment_slots_json == [{"date": "2026-09-22", "period": "afternoon"}]
    assert len(google.inserted) == 1


def test_only_mobiles_of_the_served_countries_are_texted(db: Session, google: _FakeGoogle) -> None:
    assistant = _assistant(db)
    service = AiAssistantCalendarBooking()

    assert service.visitor_channels(db, assistant, "+32 470 12 34 56") == ("+32470123456", None)
    assert service.visitor_channels(db, assistant, "+44 7700 900123") == (None, None)
    assert service.visitor_channels(db, assistant, "+1 415 555 0100") == (None, None)


def test_an_agenda_id_google_cannot_read_changes_nothing(db: Session, google: _FakeGoogle) -> None:
    assistant = _assistant(db)
    calendar = _calendar(db, assistant)
    google.failure = GoogleCalendarError("Agenda illisible (notFound)")

    with pytest.raises(ValueError, match="introuvable"):
        asyncio.run(
            AiAssistantCalendarService().update_settings(
                db, calendar, {"calendar_id": "garage@group.calendar.google.com", "duration_minutes": 30}
            )
        )

    db.rollback()
    db.refresh(calendar)
    assert (calendar.calendar_id, calendar.duration_minutes) == ("primary", None)
    google.failure = None
    asyncio.run(
        AiAssistantCalendarService().update_settings(db, calendar, {"calendar_id": "garage@group.calendar.google.com"})
    )
    assert calendar.calendar_id == "garage@group.calendar.google.com"


def test_reconnecting_another_google_account_starts_on_its_main_agenda(db: Session, google: _FakeGoogle) -> None:
    assistant = _assistant(db)
    _calendar(db, assistant, calendar_id="ancien@group.calendar.google.com")
    google.account = "autre.compte@gmail.com"

    _assistant_again, calendar = asyncio.run(
        AiAssistantCalendarService().connect(db, code="ok", state=AiAssistantCalendarState.sign(assistant.id))
    )

    assert (calendar.account_email, calendar.calendar_id) == ("autre.compte@gmail.com", "primary")


def test_the_reminder_leaves_only_the_day_before_between_9_and_20(
    db: Session, google: _FakeGoogle, outbox: dict[str, Any]
) -> None:
    assistant = _assistant(db)
    request = _request(db, assistant)
    appointment = AiAssistantAppointment(
        user_id=7,
        assistant_id=assistant.id,
        request_id=request.id,
        starts_at=_utc(_paris(24, 10)),
        ends_at=_utc(_paris(24, 11)),
        google_event_id="dlhlate",
        visitor_email="julie@example.fr",
        language="fr",
        confirmation_sent_at=datetime(2026, 9, 21, 8, 0),
        reminder_due_at=_utc(_paris(23, 10)),
        created_at=datetime(2026, 9, 21, 8, 0),
    )
    db.add(appointment)
    db.commit()

    night_before = asyncio.run(ai_assistant_appointment_notices.run_pass(db, now=_utc(_paris(23, 21, 30))))
    same_day = asyncio.run(ai_assistant_appointment_notices.run_pass(db, now=_utc(_paris(24, 1, 0))))

    assert (night_before, same_day) == (0, 0)
    db.refresh(appointment)
    assert appointment.reminder_due_at is None and appointment.reminder_sent_at is None
    assert outbox["email"].calls == []


def test_the_reminder_email_says_it_is_tomorrow(db: Session, google: _FakeGoogle, outbox: dict[str, Any]) -> None:
    assistant = _assistant(db)
    request = _request(db, assistant, contact="julie@example.fr")
    appointment = AiAssistantAppointment(
        user_id=7,
        assistant_id=assistant.id,
        request_id=request.id,
        starts_at=_utc(_paris(24, 10)),
        ends_at=_utc(_paris(24, 11)),
        google_event_id="dlhmail",
        visitor_email="julie@example.fr",
        language="fr",
        confirmation_sent_at=datetime(2026, 9, 21, 8, 0),
        reminder_due_at=_utc(_paris(23, 10)),
        created_at=datetime(2026, 9, 21, 8, 0),
    )
    db.add(appointment)
    db.commit()

    assert asyncio.run(ai_assistant_appointment_notices.run_pass(db, now=_utc(_paris(23, 10, 5)))) == 1

    [sent] = outbox["email"].calls
    assert sent["subject"].startswith("Rappel : Votre rendez-vous chez Garage Morel")
    assert "c'est demain" in sent["body_html"]


def test_the_widget_learns_how_the_confirmation_leaves(
    db: Session, google: _FakeGoogle, business_clock: list[int]
) -> None:
    assistant = _assistant(db)
    _calendar(db, assistant)
    by_sms = AiAssistantLeadRequest(
        name="Julie Roux",
        contact="06 11 22 33 44",
        session_id="s-1",
        booking=AiAssistantBookingChoice(start=_paris(22, 10)),
    )
    by_nothing = AiAssistantLeadRequest(
        name="Marc Petit",
        contact="03 83 00 00 00",
        session_id="s-2",
        booking=AiAssistantBookingChoice(start=_paris(22, 14)),
    )

    sms = asyncio.run(routes.submit_assistant_lead(assistant.slug, by_sms, VISITOR_REQUEST, db))
    nothing = asyncio.run(routes.submit_assistant_lead(assistant.slug, by_nothing, VISITOR_REQUEST, db))

    assert sms.confirmation_channel is AssistantVisitorChannel.SMS
    assert nothing.booked_start == _paris(22, 14) and nothing.confirmation_channel is None


def test_long_appointment_kinds_are_cut_not_refused() -> None:
    update = AiAssistantClientCalendarUpdate(appointment_types=["Révision complète " * 5])

    assert len(update.appointment_types[0]) > 40


def test_a_client_link_reaches_only_its_own_agenda(db: Session, google: _FakeGoogle) -> None:
    assistant = _assistant(db)
    other = _assistant(db)
    _calendar(db, assistant)
    foreign = _calendar(db, other, duration_minutes=60)
    token = AiAssistantClientLinks.token(assistant.id)

    asyncio.run(
        client_routes.update_client_calendar(
            token, AiAssistantClientCalendarUpdate(duration_minutes=30), VISITOR_REQUEST, db
        )
    )
    asyncio.run(client_routes.disconnect_client_calendar(token, VISITOR_REQUEST, db))

    db.refresh(foreign)
    assert foreign.duration_minutes == 60
    assert [calendar.assistant_id for calendar in db.query(AiAssistantCalendar).all()] == [other.id]
