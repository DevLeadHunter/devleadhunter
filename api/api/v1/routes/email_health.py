"""Email deliverability health routes (per-user, not admin-only).

Feeds the « Santé email » page: sending stats with thresholds, daily trends,
per-provider breakdown, incident journal, DNS authentication checks, Gmail
Postmaster reputation and the pre-send spam tester.
"""
import asyncio
import re
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from models.campaign import Campaign
from models.campaign_follow_up import CampaignFollowUp
from models.email_account import EmailAccount
from models.email_template import EmailTemplate
from models.user import User
from services.auth_service import require_auth
from services.email_dns_service import email_dns_service
from services.email_health_service import email_health_service
from services.email_spam_test_service import email_spam_test_service
from services.postmaster_service import postmaster_service
from services.sending_identity import describe_sending_config

router = APIRouter(prefix="/email-health", tags=["email-health"])

_ALLOWED_PERIODS: tuple[int, ...] = (7, 30, 90)


def _validated_period(period_days: int) -> int:
    """Clamp the requested window to the supported presets.

    @param period_days - Raw query value.
    @returns A supported window (falls back to 30).
    """
    return period_days if period_days in _ALLOWED_PERIODS else 30


def _domain_of(address: Optional[str]) -> str:
    """Extract the domain part of an email address.

    @param address - Full address, or already a bare domain.
    @returns The lower-cased domain (empty when *address* is empty).
    """
    return (address or "").strip().lower().rpartition("@")[2]


def _user_domains(db: Session, user: User) -> list[str]:
    """Every domain the user actually sends from.

    Covers the connected email accounts *and* the Resend sender address: Resend
    sends carry no ``EmailAccount`` row, so its domain (often a subdomain such
    as ``mail.example.fr``) would otherwise never be checked — precisely the
    domain whose authentication matters most.

    @param db - Database session.
    @param user - Authenticated user.
    @returns Lower-cased domains, deduplicated, sending domain first.
    """
    domains: list[str] = []

    def add(candidate: str) -> None:
        """Append *candidate* when it is a new, non-empty domain."""
        if candidate and candidate not in domains:
            domains.append(candidate)

    config = describe_sending_config(db, user.id)
    resend_from = config.get("resend_from_email")
    add(_domain_of(resend_from if isinstance(resend_from, str) else None))

    accounts: list[EmailAccount] = (
        db.query(EmailAccount).filter(EmailAccount.user_id == user.id).order_by(EmailAccount.id).all()
    )
    for account in accounts:
        add((account.domain or _domain_of(account.email)).strip().lower())
    return domains


class SpamTestRequest(BaseModel):
    """Draft to score before sending."""

    subject: str = Field(min_length=1, max_length=500)
    body_html: str = Field(min_length=1)


@router.get("/overview", summary="Deliverability totals + health signals")
async def email_health_overview(
    period_days: int = Query(30, description="Rolling window: 7, 30 or 90 days"),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Global and per-account stats with ok/warn/danger signals."""
    return email_health_service.overview(db, current_user.id, _validated_period(period_days))


@router.get("/trends", summary="Daily send/bounce/complaint series")
async def email_health_trends(
    period_days: int = Query(30, description="Rolling window: 7, 30 or 90 days"),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Cohort-by-send-day series for the trend charts."""
    return email_health_service.trends(db, current_user.id, _validated_period(period_days))


@router.get("/providers", summary="Deliverability per recipient mailbox provider")
async def email_health_providers(
    period_days: int = Query(30, description="Rolling window: 7, 30 or 90 days"),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Gmail/Orange/Free/SFR… breakdown — detects silent spam-filtering."""
    return email_health_service.providers(db, current_user.id, _validated_period(period_days))


@router.get("/incidents", summary="Recent bounces, complaints, suppressions, failures")
async def email_health_incidents(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Incident journal, most recent first."""
    return email_health_service.incidents(db, current_user.id, limit)


@router.get("/dns", summary="SPF / DKIM / DMARC / MX / blocklists per sending domain")
async def email_health_dns(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """DNS authentication checks for every domain the user sends from."""
    domains = _user_domains(db, current_user)
    return {"domains": [email_dns_service.check_domain(domain) for domain in domains]}


@router.get("/postmaster", summary="Gmail Postmaster reputation for the sending domains")
async def email_health_postmaster(
    period_days: int = Query(30, description="History depth (max ~120 days at Google)"),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Gmail-side domain reputation + user-reported spam rate (when configured)."""
    domains = _user_domains(db, current_user)
    return {"domains": [postmaster_service.domain_stats(domain, min(period_days, 120)) for domain in domains]}


def _follow_up_template_ids(db: Session, user_id: int) -> set[int]:
    """Template ids used as follow-ups in the user's campaigns.

    @param db - Database session.
    @param user_id - Campaign owner.
    @returns Ids referenced by ``campaign_follow_ups`` or the legacy field.
    """
    ids: set[int] = set()
    rows = (
        db.query(CampaignFollowUp.template_id)
        .join(Campaign, Campaign.id == CampaignFollowUp.campaign_id)
        .filter(Campaign.user_id == user_id)
        .all()
    )
    ids.update(int(row[0]) for row in rows if row[0] is not None)
    legacy = (
        db.query(Campaign.follow_up_template_id)
        .filter(Campaign.user_id == user_id, Campaign.follow_up_template_id.isnot(None))
        .all()
    )
    ids.update(int(row[0]) for row in legacy)
    return ids


def _initial_template_ids(db: Session, user_id: int) -> set[int]:
    """Template ids used as initial (A/B) templates in the user's campaigns.

    @param db - Database session.
    @param user_id - Campaign owner.
    @returns Ids referenced by ``template_id`` or ``ab_template_id_b``.
    """
    ids: set[int] = set()
    rows = (
        db.query(Campaign.template_id, Campaign.ab_template_id_b)
        .filter(Campaign.user_id == user_id)
        .all()
    )
    for template_id, ab_template_id in rows:
        if template_id is not None:
            ids.add(int(template_id))
        if ab_template_id is not None:
            ids.add(int(ab_template_id))
    return ids


def _template_group(template: EmailTemplate, initial_ids: set[int], follow_up_ids: set[int]) -> str:
    """Classify a template as first-contact or follow-up.

    Campaign usage wins (initial beats follow-up when both), then the name.

    @param template - The template to classify.
    @param initial_ids - Ids used as campaign initial templates.
    @param follow_up_ids - Ids used as campaign follow-ups.
    @returns ``initial`` or ``follow_up``.
    """
    if template.id in initial_ids:
        return "initial"
    if template.id in follow_up_ids:
        return "follow_up"
    if re.search(r"relance|follow.?up|rappel", template.name, flags=re.I):
        return "follow_up"
    return "initial"


@router.get("/template-scores", summary="Anti-spam score of every email template")
async def email_health_template_scores(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Score every active template automatically (nothing is sent).

    Grouped first-contact vs follow-up; results are cached 6 h per content
    hash so reloading the page does not re-hit the scoring engine.
    """
    templates: list[EmailTemplate] = (
        db.query(EmailTemplate)
        .filter(EmailTemplate.user_id == current_user.id, EmailTemplate.is_active.is_(True))
        .order_by(EmailTemplate.sort_order.desc(), EmailTemplate.id)
        .all()
    )

    # Score against the address the user really sends from — the spam engine
    # weighs the From domain, so a stale placeholder would skew every score.
    sending = describe_sending_config(db, current_user.id)
    resend_from = sending.get("resend_from_email")
    gmail_from = sending.get("gmail_email")
    active_from = gmail_from if sending.get("provider") == "gmail" else resend_from
    from_email: str = active_from if isinstance(active_from, str) and active_from else "leo@mail.dibodev.fr"

    follow_up_ids = _follow_up_template_ids(db, current_user.id)
    initial_ids = _initial_template_ids(db, current_user.id)

    semaphore = asyncio.Semaphore(3)

    async def score(template: EmailTemplate) -> dict[str, Any]:
        """Score one template (bounded concurrency).

        @param template - The template to score.
        @returns Its scoring payload.
        """
        async with semaphore:
            result = await email_spam_test_service.test_cached(
                subject=template.subject,
                body_html=template.body_html,
                from_email=from_email,
                to_email="test@example.com",
            )
        # The unsubscribe footer is appended by the sending pipeline
        # (unsubscribe_service.add_unsubscribe_footer) — flagging a template
        # for not embedding it would be a false alarm.
        checks = [
            {**check, "status": "ok", "detail": "Ajouté automatiquement par DevLeadHunter à l'envoi."}
            if check["key"] == "unsubscribe" and check["status"] != "ok"
            else check
            for check in result["checks"]
        ]
        issues = [check for check in checks if check["status"] != "ok"]
        return {
            "id": template.id,
            "name": template.name,
            "subject": template.subject,
            "group": _template_group(template, initial_ids, follow_up_ids),
            "spamassassin": result["spamassassin"],
            "checks": checks,
            "issues": issues,
        }

    scored = list(await asyncio.gather(*(score(template) for template in templates)))
    return {
        "initial": [item for item in scored if item["group"] == "initial"],
        "follow_up": [item for item in scored if item["group"] == "follow_up"],
    }


@router.post("/spam-test", summary="Score an email draft before sending")
async def email_health_spam_test(
    request: SpamTestRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """SpamAssassin score (free Postmark endpoint) + local French-cold-email checks."""
    default_account: EmailAccount | None = (
        db.query(EmailAccount)
        .filter(EmailAccount.user_id == current_user.id)
        .order_by(EmailAccount.is_default.desc(), EmailAccount.id)
        .first()
    )
    if default_account is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configurez d'abord un compte d'envoi pour tester un email.",
        )
    return await email_spam_test_service.test(
        subject=request.subject,
        body_html=request.body_html,
        from_email=default_account.email,
        to_email="test@example.com",
    )
