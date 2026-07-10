"""
Main FastAPI application entry point.
"""
import logging

def _configure_logging() -> None:
    """Configure app log levels without overriding uvicorn reload workers."""
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.WARNING,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        )

    # SQLAlchemy logs all SQL queries at INFO level - reduce to ERROR
    sqlalchemy_engine_logger = logging.getLogger('sqlalchemy.engine')
    sqlalchemy_engine_logger.setLevel(logging.ERROR)
    sqlalchemy_engine_logger.propagate = False

    sqlalchemy_pool_logger = logging.getLogger('sqlalchemy.pool')
    sqlalchemy_pool_logger.setLevel(logging.ERROR)
    sqlalchemy_pool_logger.propagate = False

    sqlalchemy_dialects_logger = logging.getLogger('sqlalchemy.dialects')
    sqlalchemy_dialects_logger.setLevel(logging.ERROR)
    sqlalchemy_dialects_logger.propagate = False

    logging.getLogger('stripe').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.WARNING)


_configure_logging()
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from api.v1.router import router as api_router
from core.config import settings
from services.scraper_service import scraper_service
from scrappers.google_scraper import GoogleScraper
from scrappers.pagesjaunes_scraper import PagesJaunesScraper
from scrappers.osm_scraper import OSMScraper
from scrappers.auto_scraper import AutoScraper
from scrappers.brightdata_scraper import BrightDataScraper
from services.demo_site_cleanup_service import run_demo_site_cleanup_loop
from services.email_queue_worker import run_queue_worker
from core.win32_asyncio import ensure_proactor_event_loop

ensure_proactor_event_loop()


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# Initialize FastAPI app
app = FastAPI(
    title="Prospect Tool API",
    description="Personal prospect research tool API for freelance web developers",
    version="Hunter",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Return a clean 500 that still carries CORS headers.

    Starlette emits its default 500 above the CORS middleware, so the browser sees
    "CORS header missing" instead of the real error. We log the exception and re-add
    the CORS headers (based on the request Origin) so the frontend gets a proper error.

    Args:
        request: The incoming request that failed.
        exc: The unhandled exception raised while processing the request.

    Returns:
        A JSON 500 response with CORS headers when the Origin is allowed.
    """
    logging.getLogger(__name__).exception(
        "Unhandled error on %s %s", request.method, request.url.path
    )
    headers: dict = {}
    origin = request.headers.get("origin")
    if origin and origin in settings.allowed_cors_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Vary"] = "Origin"
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
        headers=headers,
    )


# Include API routes
app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
async def startup_event() -> None:
    """
    Initialize services on application startup.
    
    This function runs when the FastAPI application starts.
    It sets up scrapers and other services.
    """
    # Register scrapers
    google_scraper = GoogleScraper()
    await scraper_service.add_scraper(google_scraper)
    
    pagesjaunes_scraper = PagesJaunesScraper()
    await scraper_service.add_scraper(pagesjaunes_scraper)

    osm_scraper = OSMScraper()
    await scraper_service.add_scraper(osm_scraper)

    auto_scraper = AutoScraper()
    await scraper_service.add_scraper(auto_scraper)

    brightdata_scraper = BrightDataScraper()
    await scraper_service.add_scraper(brightdata_scraper)

    import asyncio

    asyncio.create_task(run_demo_site_cleanup_loop())
    asyncio.create_task(run_queue_worker())
    asyncio.create_task(_warmup_maps_autocomplete())


async def _warmup_maps_autocomplete() -> None:
    """Optionally warm nodriver Chrome for Google Maps autocomplete."""
    try:
        if not settings.scraper_warmup_maps:
            return
        from scrappers.nodriver_browser import NODRIVER_AVAILABLE
        from scrappers.nodriver_executor import run_nodriver_task
        from scrappers.google_scraper import warmup_maps_suggestion_session

        if not NODRIVER_AVAILABLE:
            return
        await run_nodriver_task(lambda: warmup_maps_suggestion_session(), timeout=60)
        logging.getLogger(__name__).info("Google Maps autocomplete session ready")
    except Exception as exc:
        logging.getLogger(__name__).warning("Google Maps autocomplete warmup skipped: %s", exc)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Cleanup on application shutdown.
    
    This function runs when the FastAPI application shuts down.
    It performs cleanup tasks.
    """
    pass


@app.get("/", tags=["root"])
async def root() -> dict:
    """
    Root endpoint.
    
    Returns:
        Welcome message and API information
    """
    return {
        "message": "Welcome to Prospect Tool API",
        "version": "Hunter",
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="warning",  # Reduce uvicorn logs to warnings only
        access_log=False  # Disable HTTP access logs
    )

