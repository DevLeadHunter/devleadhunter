"""
Main FastAPI application entry point.
"""

import asyncio
import logging


def _configure_logging() -> None:
    """Configure app log levels without overriding uvicorn reload workers."""
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.WARNING,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    # SQLAlchemy logs all SQL queries at INFO level - reduce to ERROR
    sqlalchemy_engine_logger = logging.getLogger("sqlalchemy.engine")
    sqlalchemy_engine_logger.setLevel(logging.ERROR)
    sqlalchemy_engine_logger.propagate = False

    sqlalchemy_pool_logger = logging.getLogger("sqlalchemy.pool")
    sqlalchemy_pool_logger.setLevel(logging.ERROR)
    sqlalchemy_pool_logger.propagate = False

    sqlalchemy_dialects_logger = logging.getLogger("sqlalchemy.dialects")
    sqlalchemy_dialects_logger.setLevel(logging.ERROR)
    sqlalchemy_dialects_logger.propagate = False

    logging.getLogger("stripe").setLevel(logging.WARNING)
    # The per-call provider / latency / cost line of the AI assistant's models (INFO, above the root level).
    logging.getLogger("services.ai_assistant.llm_router").setLevel(logging.INFO)
    # The size of each assistant prompt (INFO): how much of the site and the documents it carries.
    logging.getLogger("services.ai_assistant.chat_service").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)


_configure_logging()
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.v1.router import router as api_router
from core.config import settings
from core.rate_limiter import limiter
from core.win32_asyncio import ensure_proactor_event_loop
from scrappers.auto_scraper import AutoScraper
from scrappers.brightdata_scraper import BrightDataScraper
from scrappers.facebook_search_scraper import FacebookSearchScraper
from scrappers.google_scraper import GoogleScraper
from scrappers.osm_scraper import OSMScraper
from scrappers.pagesjaunes_scraper import PagesJaunesScraper
from services.acquisition_orchestrator import acquisition_orchestrator
from services.ai_assistant.cleanup_service import run_ai_assistant_cleanup_loop
from services.ai_assistant.report_service import ai_assistant_report_service
from services.ai_assistant.request_runner import run_ai_assistant_request_loop
from services.ai_assistant.source_service import ai_assistant_source_service
from services.demo_site_cleanup_service import run_demo_site_cleanup_loop
from services.email_queue_worker import email_queue_worker
from services.notification_service import notification_service, run_daily_recap_loop
from services.order_fulfillment_recovery_service import run_order_fulfillment_recovery_loop
from services.order_payment_reconciliation_service import run_order_payment_reconciliation_loop
from services.scraper_service import scraper_service
from services.send_queue_watchdog_service import run_send_queue_watchdog_loop
from services.sms_automation_service import run_sms_automation_loop

ensure_proactor_event_loop()


# Initialize FastAPI app
app = FastAPI(
    title="Prospect Tool API",
    description="Personal prospect research tool API for freelance web developers",
    version="Hunter",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
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


_background_tasks: set[asyncio.Task] = set()


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
    logging.getLogger(__name__).exception("Unhandled error on %s %s", request.method, request.url.path)
    # Notify admins of the crash without blocking the error response (fire-and-forget).
    task = asyncio.create_task(
        notification_service.notify_error(
            context=request.url.path,
            message=str(exc),
            tag=f"error:{request.url.path}",
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
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

    # Explicit-only source (_ISOLATED_SOURCES): a generic search never cascades into
    # Facebook, and an explicit Facebook search never falls back to the generic chain.
    facebook_scraper = FacebookSearchScraper()
    await scraper_service.add_scraper(facebook_scraper)

    # A video generation task lives only in memory, so a restart (crash, OOM kill,
    # deploy) orphans any site left mid-render — request_generation then refuses to
    # restart it and the dashboard polls it forever. Reset those to failed at boot.
    from core.database import SessionLocal
    from services.assistant_video_service import assistant_video_service
    from services.demo_video_service import demo_video_service

    reconcile_db = SessionLocal()
    try:
        reset = demo_video_service.reconcile_orphaned(reconcile_db)
        if reset:
            logging.getLogger(__name__).info("Reset %d orphaned demo video generation(s) at startup", reset)
        reset_assistant = assistant_video_service.reconcile_orphaned(reconcile_db)
        if reset_assistant:
            logging.getLogger(__name__).info(
                "Reset %d orphaned assistant video generation(s) at startup", reset_assistant
            )
    finally:
        reconcile_db.close()

    # Keep a strong reference to every long-lived loop, else asyncio may GC the task and it dies silently.
    for coro in (
        run_demo_site_cleanup_loop(),
        run_ai_assistant_cleanup_loop(),
        run_ai_assistant_request_loop(),
        ai_assistant_report_service.run_loop(),
        ai_assistant_source_service.run_loop(),
        email_queue_worker.run_forever(),
        run_order_fulfillment_recovery_loop(),
        run_order_payment_reconciliation_loop(),
        acquisition_orchestrator.run_forever(),
        _warmup_maps_autocomplete(),
        run_daily_recap_loop(),
        run_send_queue_watchdog_loop(),
        run_sms_automation_loop(),
    ):
        task = asyncio.create_task(coro)
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)


async def _warmup_maps_autocomplete() -> None:
    """Optionally warm nodriver Chrome for Google Maps autocomplete."""
    try:
        if not settings.scraper_warmup_maps:
            return
        from scrappers.google_scraper import warmup_maps_suggestion_session
        from scrappers.nodriver_browser import NODRIVER_AVAILABLE
        from scrappers.nodriver_executor import run_nodriver_task

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
        "health": f"{settings.api_prefix}/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="warning",  # Reduce uvicorn logs to warnings only
        access_log=False,  # Disable HTTP access logs
    )
