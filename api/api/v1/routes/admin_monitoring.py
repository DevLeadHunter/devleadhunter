"""
Admin-only monitoring endpoints.

Surface the *reactive* diagnostics captured during real scraping runs (per-source
health, incidents, and the HTML captured when a source was blocked) plus a live DB
probe — so an admin can see "Google broke" and grab the new markup, without any
proactive probing. All endpoints require an admin (``require_admin``).
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User
from services.auth_service import require_admin
from services.scraper_diagnostics_service import scraper_diagnostics_service

router = APIRouter(prefix="/admin/monitoring", tags=["admin-monitoring"])


@router.get("/overview")
async def monitoring_overview(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Live system health + per-source scraping health (last 24 h)."""
    database_healthy = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_healthy = False

    return {
        "database": "healthy" if database_healthy else "unhealthy",
        "diagnostics_total": scraper_diagnostics_service.total_count(db),
        "sources": scraper_diagnostics_service.source_health(db),
    }


@router.get("/scrapers/incidents")
async def scraper_incidents(
    limit: int = Query(100, ge=1, le=500),
    source: str | None = Query(None, description="Filter by source value"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Recent per-source run outcomes (ok / empty / blocked / timeout / error)."""
    rows = scraper_diagnostics_service.recent(db, limit=limit, source=source)
    return {
        "items": [
            {
                "id": row.id,
                "source": row.source,
                "status": row.status,
                "category": row.category,
                "city": row.city,
                "results_count": row.results_count,
                "expected_count": row.expected_count,
                "error_message": row.error_message,
                "has_html": bool(row.html_snapshot),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }


@router.get("/scrapers/incidents/{diagnostic_id}/html")
async def scraper_incident_html(
    diagnostic_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    """Return the raw HTML captured when a source was blocked.

    Served as ``text/plain`` on purpose: the admin inspects the raw markup to write a
    new selector, and it must NOT be rendered (the page is site/attacker-controlled).
    """
    row = scraper_diagnostics_service.get(db, diagnostic_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnostic not found")
    if not row.html_snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No HTML captured for this incident")
    return Response(content=row.html_snapshot, media_type="text/plain; charset=utf-8")
