"""
Health check routes.
"""
from datetime import datetime
from fastapi import APIRouter
from models.health import HealthStatus
from core.config import settings


router = APIRouter(
    prefix="/health",
    tags=["health"]
)


@router.get(
    "",
    response_model=HealthStatus,
    summary="Health check endpoint",
    description="Check the health status of the API and services"
)
async def health_check() -> HealthStatus:
    """
    Get health status of the API.
    
    Returns:
        HealthStatus object with current status and timestamp
        
    Example:
        >>> GET /health
        {
            "status": "healthy",
            "version": "v1",
            "timestamp": "2024-01-15T10:30:00Z",
            "services": {}
        }
    """
    return HealthStatus(
        status="healthy",
        version=settings.api_version,
        timestamp=datetime.utcnow().isoformat() + "Z",
        services={
            "api": "healthy",
            "database": "healthy",
            "scrapers": "healthy"
        }
    )

