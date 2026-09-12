"""The SMS forecast is forward-looking.

A relance is projected on its first-email-plus-delay day, so a prospect emailed
recently already appears weeks ahead — not only once the delay has fully elapsed.
The worker's throttle (per-pass and daily caps, legal window) is replayed forward.
"""

import importlib
import pkgutil
from datetime import datetime, timedelta
from types import SimpleNamespace

from sqlalchemy.orm import configure_mappers

import models as _models_pkg

# Importing the service pulls in ORM models whose cross-relationships must resolve.
for _module in pkgutil.iter_modules(_models_pkg.__path__):
    importlib.import_module(f"models.{_module.name}")
configure_mappers()

import services.sms_automation_service as sas  # noqa: E402
from services.sms_relance_service import SmsRelanceCandidate  # noqa: E402


def _candidate(prospect_id: int, emailed_at: datetime | None, cold: bool = False) -> SmsRelanceCandidate:
    prospect = SimpleNamespace(
        id=prospect_id, name=f"Prospect {prospect_id}", email=None, city="Lyon", category="barber"
    )
    demo = SimpleNamespace(id=100 + prospect_id, site_reviewed_at=None)
    return SmsRelanceCandidate(
        prospect=prospect,
        demo_site=demo,
        demo_url=f"https://demo.dibodev.fr/s/p{prospect_id}",
        emailed_at=emailed_at,
        cold=cold,
    )


def _configure(
    monkeypatch,
    *,
    relance: bool,
    cold: bool,
    after_days: int = 30,
    relance_candidates: list[SmsRelanceCandidate] | None = None,
    cold_candidates: list[SmsRelanceCandidate] | None = None,
    sent_today: int = 0,
) -> None:
    """Wire the forecast's collaborators to fakes so only the projection logic is tested."""
    monkeypatch.setattr(sas, "smsmode_provider", SimpleNamespace(is_configured=True))
    config = SimpleNamespace(
        user_id=1,
        sender="Dibodev",
        auto_relance_enabled=relance,
        cold_sms_enabled=cold,
        auto_relance_after_days=after_days,
    )
    monkeypatch.setattr(sas, "sms_config_service", SimpleNamespace(get=lambda db, user_id: config))
    monkeypatch.setattr(
        sas,
        "sms_relance_service",
        SimpleNamespace(
            find_relance_projection_candidates=lambda db, user_id, **kwargs: list(relance_candidates or []),
            find_cold_candidates=lambda db, user_id, **kwargs: list(cold_candidates or []),
        ),
    )
    monkeypatch.setattr(sas.SmsAutomationService, "_sent_today", lambda self, db, user_id: sent_today)


def test_recent_relance_is_projected_at_email_plus_delay(monkeypatch):
    emailed_at = datetime.utcnow() - timedelta(days=15)  # J+30 lands ~15 days out
    _configure(monkeypatch, relance=True, cold=False, relance_candidates=[_candidate(1, emailed_at)])

    start = datetime.utcnow() - timedelta(days=1)
    end = datetime.utcnow() + timedelta(days=45)
    rows = sas.sms_automation_service.forecast_rows(None, 1, start, end)

    assert len(rows) == 1
    assert rows[0]["queue_type"] == "sms_relance"
    assert rows[0]["prospect_id"] == 1
    scheduled = datetime.fromisoformat(rows[0]["scheduled_at"])
    # Placed near email + 30 days, never dumped at "now".
    assert datetime.utcnow() + timedelta(days=12) < scheduled < datetime.utcnow() + timedelta(days=19)


def test_recent_relance_is_absent_from_the_current_week(monkeypatch):
    emailed_at = datetime.utcnow() - timedelta(days=15)
    _configure(monkeypatch, relance=True, cold=False, relance_candidates=[_candidate(1, emailed_at)])

    start = datetime.utcnow() - timedelta(days=1)
    end = datetime.utcnow() + timedelta(days=2)  # this week: the J+30 lands later, so nothing shows
    rows = sas.sms_automation_service.forecast_rows(None, 1, start, end)

    assert rows == []


def test_projection_respects_the_daily_cap(monkeypatch):
    emailed_at = datetime.utcnow() - timedelta(days=60)  # all already past the delay
    candidates = [_candidate(prospect_id, emailed_at) for prospect_id in range(1, 26)]
    _configure(monkeypatch, relance=True, cold=False, relance_candidates=candidates)

    start = datetime.utcnow() - timedelta(days=1)
    end = datetime.utcnow() + timedelta(days=15)
    rows = sas.sms_automation_service.forecast_rows(None, 1, start, end)

    assert len(rows) == 25
    per_day: dict[str, int] = {}
    for row in rows:
        day = datetime.fromisoformat(row["scheduled_at"]).date().isoformat()
        per_day[day] = per_day.get(day, 0) + 1
    assert all(count <= 20 for count in per_day.values())  # daily cap never exceeded
    assert len(per_day) >= 2  # 25 with a 20/day cap must spill onto a second day
