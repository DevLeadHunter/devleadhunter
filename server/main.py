"""
Main FastAPI application entry point.
"""
# Configure logging FIRST, before any other imports that might use logging
import logging

# Set default level to WARNING to reduce noise
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # Force reconfiguration if already configured
)

# Configure specific loggers to reduce verbosity BEFORE importing modules that use them
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

# Stripe SDK logs all API requests at INFO level - reduce to WARNING
logging.getLogger('stripe').setLevel(logging.WARNING)

# Uvicorn access logs are handled separately via uvicorn config
# But we can reduce internal uvicorn logs
logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
logging.getLogger('uvicorn.error').setLevel(logging.WARNING)

# NOW import other modules after logging is configured
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from api.v1.router import router as api_router
from core.config import settings
from services.scraper_service import scraper_service
from scrappers.mock_scraper import MockScraper
from scrappers.google_scraper import GoogleScraper
from scrappers.pagesjaunes_scraper import PagesJaunesScraper
from scrappers.yelp_scraper import YelpScraper
from scrappers.osm_scraper import OSMScraper
from scrappers.mappy_scraper import MappyScraper


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
    mock_scraper = MockScraper()
    await scraper_service.add_scraper(mock_scraper)
    
    google_scraper = GoogleScraper()
    await scraper_service.add_scraper(google_scraper)
    
    pagesjaunes_scraper = PagesJaunesScraper()
    await scraper_service.add_scraper(pagesjaunes_scraper)
    
    yelp_scraper = YelpScraper()
    await scraper_service.add_scraper(yelp_scraper)
    
    osm_scraper = OSMScraper()
    await scraper_service.add_scraper(osm_scraper)
    
    mappy_scraper = MappyScraper()
    await scraper_service.add_scraper(mappy_scraper)


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

