"""Unit tests for `{lien_demo}` rendering and `{date_expiration}` resolution.

The demo link MUST be a real ``<a>`` anchor: Resend's click tracking only rewrites
``href`` attributes, so a bare URL in the body was never wrapped and every click went
untracked. These tests lock the anchor rendering so the tracking gap cannot silently
reappear.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from core.config import settings
from services.campaign_queue_service import CampaignQueueService
from services.email_variables import EmailVariables


class _FakeDB:
    """Fake session whose ``execute().scalar_one_or_none()`` returns a canned demo site."""

    def __init__(self, site: object | None) -> None:
        self._site = site

    def execute(self, *args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(scalar_one_or_none=lambda: self._site)


def test_build_demo_link_html_wraps_url_in_anchor() -> None:
    """A demo URL renders as an anchor carrying the exact href (so Resend can wrap it)."""
    html = EmailVariables.build_demo_link_html("https://demo.dibodev.fr/tacos-maru?v=A")
    assert html.startswith("<a ")
    assert 'href="https://demo.dibodev.fr/tacos-maru?v=A"' in html
    assert html.endswith("</a>")


def test_build_demo_link_html_shows_trimmed_url_as_default_text() -> None:
    """By default the visible text is the host/slug — no scheme, no A/B query."""
    html = EmailVariables.build_demo_link_html("https://demo.dibodev.fr/tacos-maru?v=A")
    assert ">demo.dibodev.fr/tacos-maru</a>" in html
    assert "?v=A</a>" not in html


def test_build_demo_link_html_accepts_custom_text() -> None:
    """The visible call-to-action text can be overridden by the caller."""
    html = EmailVariables.build_demo_link_html("https://demo.dibodev.fr/x", text="le comparer")
    assert ">le comparer</a>" in html


def test_build_demo_link_html_empty_when_no_link() -> None:
    """No demo link renders empty (the queue guard skips demo-less prospects)."""
    assert EmailVariables.build_demo_link_html("") == ""


def test_format_expiry_date_renders_french_day_month() -> None:
    """The expiry date reads as a plain French date, whatever the server locale."""
    assert EmailVariables.format_expiry_date(datetime(2026, 10, 12, tzinfo=UTC)) == "12 octobre"


def test_resolve_expiry_date_uses_started_ttl() -> None:
    """A demo whose TTL already runs announces its stored expiry day."""
    site = SimpleNamespace(
        demo_link_sent_at=datetime(2026, 9, 21, 6, 0, 0),
        expires_at=datetime(2026, 10, 12, 6, 0, 0),
    )
    resolved = EmailVariables.resolve_expiry_date(_FakeDB(site), "https://demo.dibodev.fr/tacos-maru?src=email&v=A")
    assert resolved == "12 octobre"


def test_resolve_expiry_date_projects_ttl_for_first_send() -> None:
    """Before the first send, the announced date is today plus the TTL (this send starts the clock)."""
    site = SimpleNamespace(demo_link_sent_at=None, expires_at=datetime(2099, 12, 31))
    expected = EmailVariables.format_expiry_date(datetime.now(UTC) + timedelta(days=settings.demo_site_ttl_days))
    assert EmailVariables.resolve_expiry_date(_FakeDB(site), "https://demo.dibodev.fr/tacos-maru") == expected


def test_resolve_expiry_date_empty_without_demo() -> None:
    """No demo link, or an unknown slug, renders empty instead of a wrong date."""
    assert EmailVariables.resolve_expiry_date(_FakeDB(None), "") == ""
    assert EmailVariables.resolve_expiry_date(_FakeDB(None), "https://demo.dibodev.fr/inconnu") == ""


def test_template_using_expiry_date_requires_demo() -> None:
    """A template holding only {date_expiration} still triggers the demo guard."""
    template = SimpleNamespace(
        subject="Dernier rappel", body_html="Votre site reste en ligne jusqu'au {date_expiration}."
    )
    assert CampaignQueueService._template_uses_demo_link(template) is True


class _FakeAssistantDB:
    """Fake session whose ``execute().scalars().first()`` returns a canned assistant."""

    def __init__(self, assistant: object | None) -> None:
        self._assistant = assistant

    def execute(self, *args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: self._assistant))


def test_resolve_assistant_link_renders_anchor_for_active_assistant() -> None:
    """`{lien_assistant}` renders a real anchor to the assistant's demo page."""
    html = EmailVariables.resolve_assistant_link(_FakeAssistantDB(SimpleNamespace(slug="agence-immo")), 1)
    assert html.startswith("<a ")
    assert "/a/agence-immo" in html
    assert html.endswith("</a>")


def test_resolve_assistant_link_empty_without_assistant() -> None:
    """`{lien_assistant}` is empty when the prospect has no active assistant."""
    assert EmailVariables.resolve_assistant_link(_FakeAssistantDB(None), 1) == ""
