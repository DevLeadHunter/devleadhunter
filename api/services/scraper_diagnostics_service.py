"""Reactive diagnostics for the scraping sources (health + incident capture).

The orchestrator calls :meth:`record` after every source run; blocks additionally carry
the captured HTML. The admin monitoring page reads :meth:`recent`, :meth:`source_health`
and :meth:`get`. Writes open their own short-lived session (the orchestrator does not
thread a DB session through), and never raise into the scraping flow.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database import SessionLocal
from models.scraper_diagnostic import ScraperDiagnostic

logger = logging.getLogger(__name__)

# Outcome statuses.
STATUS_OK: str = "ok"
STATUS_EMPTY: str = "empty"
STATUS_BLOCKED: str = "blocked"
STATUS_TIMEOUT: str = "timeout"
STATUS_ERROR: str = "error"

# Statuses that indicate the source is degraded (drives the red/amber badges).
DEGRADED_STATUSES: frozenset[str] = frozenset({STATUS_BLOCKED, STATUS_TIMEOUT, STATUS_ERROR})

# Keep incident history bounded so html_snapshot rows do not grow forever.
_RETENTION_DAYS: int = 30


class ScraperDiagnosticsService:
    """Persist and read per-source scraping health."""

    def record(
        self,
        *,
        source: str,
        status: str,
        category: Optional[str] = None,
        city: Optional[str] = None,
        results_count: int = 0,
        expected_count: Optional[int] = None,
        error_message: Optional[str] = None,
        html_snapshot: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> None:
        """Persist one source-run outcome (best-effort — never raises).

        Opens its own session so the orchestrator does not have to thread one through.
        """
        db = SessionLocal()
        try:
            row = ScraperDiagnostic(
                source=source,
                status=status,
                category=(category or None),
                city=(city or None),
                results_count=int(results_count or 0),
                expected_count=expected_count,
                error_message=(error_message[:500] if error_message else None),
                html_snapshot=html_snapshot,
                user_id=user_id,
            )
            db.add(row)
            db.commit()
            self._prune(db)
        except Exception as exc:  # noqa: BLE001 — diagnostics must never break scraping
            logger.warning("Failed to record scraper diagnostic (%s/%s): %s", source, status, exc)
            db.rollback()
        finally:
            db.close()

    def _prune(self, db: Session) -> None:
        """Delete diagnostics older than the retention window (keeps the table bounded)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=_RETENTION_DAYS)
        try:
            db.query(ScraperDiagnostic).filter(ScraperDiagnostic.created_at < cutoff).delete(
                synchronize_session=False
            )
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()

    def recent(
        self, db: Session, *, limit: int = 100, source: Optional[str] = None
    ) -> list[ScraperDiagnostic]:
        """Return the most recent diagnostics (optionally filtered by source)."""
        query = db.query(ScraperDiagnostic)
        if source:
            query = query.filter(ScraperDiagnostic.source == source)
        return query.order_by(ScraperDiagnostic.created_at.desc()).limit(limit).all()

    def get(self, db: Session, diagnostic_id: int) -> Optional[ScraperDiagnostic]:
        """Fetch a single diagnostic (used to view its captured HTML)."""
        return db.query(ScraperDiagnostic).filter(ScraperDiagnostic.id == diagnostic_id).first()

    def source_health(self, db: Session) -> list[dict[str, object]]:
        """Summarise health per source over the last 24 h.

        @param db - Database session.
        @returns One entry per source seen recently: latest status, last-ok timestamp,
            counts of runs/incidents in the last 24 h, and the id of the latest incident
            with a captured HTML snapshot (for a one-click "view HTML").
        """
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        rows: list[ScraperDiagnostic] = (
            db.query(ScraperDiagnostic)
            .filter(ScraperDiagnostic.created_at >= since)
            .order_by(ScraperDiagnostic.created_at.desc())
            .all()
        )

        by_source: dict[str, list[ScraperDiagnostic]] = {}
        for row in rows:
            by_source.setdefault(row.source, []).append(row)

        health: list[dict[str, object]] = []
        for source, entries in by_source.items():
            latest = entries[0]  # rows are desc by created_at
            last_ok = next((e for e in entries if e.status == STATUS_OK), None)
            incidents = [e for e in entries if e.status in DEGRADED_STATUSES]
            latest_with_html = next((e for e in entries if e.html_snapshot), None)
            health.append(
                {
                    "source": source,
                    "latest_status": latest.status,
                    "latest_at": latest.created_at.isoformat() if latest.created_at else None,
                    "runs_24h": len(entries),
                    "incidents_24h": len(incidents),
                    "last_ok_at": last_ok.created_at.isoformat() if last_ok and last_ok.created_at else None,
                    "latest_incident_id": latest_with_html.id if latest_with_html else None,
                }
            )
        health.sort(key=lambda item: str(item["source"]))
        return health

    def total_count(self, db: Session) -> int:
        """Total number of stored diagnostics."""
        return int(db.query(func.count(ScraperDiagnostic.id)).scalar() or 0)


scraper_diagnostics_service = ScraperDiagnosticsService()
