"""
Health check routes.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from models.health import HealthStatus


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/health",
    tags=["health"]
)


@router.get(
    "",
    response_model=HealthStatus,
    summary="Health check endpoint",
    description="Check the health status of the API and its database (usable for uptime monitoring)."
)
async def health_check(
    response: Response,
    db: Session = Depends(get_db),
) -> HealthStatus:
    """
    Report the real health of the API and its database.

    The database is actually probed with ``SELECT 1``; when it fails the endpoint
    returns HTTP 503 so an uptime monitor detects the outage (instead of the old
    hard-coded "healthy" that could never fail). Scrapers are on-demand jobs, not a
    persistent service, so they are not falsely reported here.

    Args:
        response: Injected so the status code can flip to 503 on a DB failure.
        db: Database session used for the connectivity probe.

    Returns:
        HealthStatus with per-service statuses and an overall status.
    """
    services: dict[str, str] = {"api": "healthy"}
    overall_status: str = "healthy"

    try:
        db.execute(text("SELECT 1"))
        services["database"] = "healthy"
    except Exception as exc:  # noqa: BLE001 — any DB error means the service is down
        logger.warning("Health check DB probe failed: %s", exc)
        services["database"] = "unhealthy"
        overall_status = "unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthStatus(
        status=overall_status,
        version=settings.api_version,
        timestamp=datetime.utcnow().isoformat() + "Z",
        services=services,
    )
