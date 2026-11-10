"""
Main API v1 router.
"""

from fastapi import APIRouter

from .product_module_mounting import include_product_module_routers
from .routes import (
    accounting,
    admin_monitoring,
    admin_storage,
    admin_storyblok,
    auth,
    automations,
    behavior,
    campaigns,
    countries,
    credit_settings,
    credits,
    dashboard,
    demo_events,
    demo_sites,
    desktop_jobs,
    domains,
    email_accounts,
    email_health,
    email_signatures,
    email_templates,
    emails,
    enrichment,
    exports,
    health,
    interactions,
    notifications,
    orders,
    organizations,
    payment_accounts,
    payments,
    product_modules,
    prospect_searches,
    prospects,
    send_policy,
    site_contact,
    sms,
    sources,
    support,
    unsubscribe,
    users,
    webhooks,
)
from .routes import (
    settings as settings_routes,
)

router = APIRouter(prefix="", tags=["v1"])


# Include all route modules
router.include_router(auth.router)
router.include_router(health.router)
router.include_router(prospects.router)
router.include_router(prospect_searches.router)
router.include_router(desktop_jobs.router)
router.include_router(users.router)
router.include_router(credit_settings.router)
router.include_router(credits.router)
router.include_router(payments.router)
router.include_router(accounting.router)
router.include_router(support.router)
router.include_router(email_accounts.router)
router.include_router(email_templates.router)
router.include_router(email_signatures.router)
router.include_router(emails.router)
router.include_router(email_health.router)
router.include_router(campaigns.router)
router.include_router(unsubscribe.router)
router.include_router(exports.router)
router.include_router(interactions.router)
router.include_router(notifications.router)
router.include_router(demo_events.router)
router.include_router(demo_sites.router)
# The installed product modules (the receptionist, the Apple Wallet cards…), each behind its switch, mounted here
# where the receptionist's routers always were.
include_product_module_routers(router)
router.include_router(domains.router)
router.include_router(enrichment.router)
router.include_router(orders.router)
router.include_router(payment_accounts.router)
router.include_router(dashboard.router)
router.include_router(behavior.router)
router.include_router(sources.router)
router.include_router(countries.router)
router.include_router(webhooks.router)
router.include_router(admin_storage.router)
router.include_router(organizations.router)
router.include_router(settings_routes.router)
router.include_router(admin_monitoring.router)
router.include_router(admin_storyblok.router)
router.include_router(automations.router)
router.include_router(send_policy.router)
router.include_router(sms.router)
router.include_router(site_contact.router)
router.include_router(product_modules.router)
