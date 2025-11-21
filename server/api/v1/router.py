"""
Main API v1 router.
"""
from fastapi import APIRouter
from .routes import (
    health, prospects, auth, users, credit_settings, credits, payments, 
    accounting, support, email_accounts, email_templates, emails, scraping_jobs,
    campaigns, unsubscribe, exports, interactions
)
from core.config import settings


router = APIRouter(
    prefix="",
    tags=["v1"]
)


# Include all route modules
router.include_router(auth.router)
router.include_router(health.router)
router.include_router(prospects.router)
router.include_router(scraping_jobs.router)
router.include_router(users.router)
router.include_router(credit_settings.router)
router.include_router(credits.router)
router.include_router(payments.router)
router.include_router(accounting.router)
router.include_router(support.router)
router.include_router(email_accounts.router)
router.include_router(email_templates.router)
router.include_router(emails.router)
router.include_router(campaigns.router)
router.include_router(unsubscribe.router)
router.include_router(exports.router)
router.include_router(interactions.router)

