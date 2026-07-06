"""Dashboard home KPIs aggregated for the current user."""
import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from models.campaign import Campaign, CampaignStatus
from models.demo_site import DemoSite
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from models.user import User
from schemas.dashboard import (
    ActivityPoint,
    DashboardActivityResponse,
    DashboardStatsResponse,
    HotLeadResponse,
    HotLeadsResponse,
)
from services.auth_service import get_current_active_user
from services.behavior_service import behavior_service
from services.order_service import order_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _count(db: Session, stmt: Select) -> int:
    """Run a COUNT over a filtered statement."""
    return int(db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0)


@router.get("/stats", response_model=DashboardStatsResponse)
async def dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DashboardStatsResponse:
    """Return the headline KPIs for the dashboard home page."""
    uid = current_user.id

    prospects_total = _count(db, select(ProspectDB.id).where(ProspectDB.user_id == uid))
    demo_sites_active = _count(
        db,
        select(DemoSite.id).where(
            DemoSite.user_id == uid, DemoSite.status == DemoSiteStatus.ACTIVE.value
        ),
    )
    campaigns_active = _count(
        db,
        select(Campaign.id).where(
            Campaign.user_id == uid, Campaign.status == CampaignStatus.ACTIVE.value
        ),
    )

    emails_sent = _count(
        db, select(EmailLog.id).where(EmailLog.user_id == uid, EmailLog.sent_at.isnot(None))
    )
    emails_opened = _count(
        db, select(EmailLog.id).where(EmailLog.user_id == uid, EmailLog.opened_at.isnot(None))
    )
    emails_clicked = _count(
        db, select(EmailLog.id).where(EmailLog.user_id == uid, EmailLog.clicked_at.isnot(None))
    )

    open_rate = round(emails_opened / emails_sent * 100, 2) if emails_sent else 0.0
    click_rate = round(emails_clicked / emails_sent * 100, 2) if emails_sent else 0.0

    sales = order_service.stats_for_user(db, uid)

    return DashboardStatsResponse(
        prospects_total=prospects_total,
        demo_sites_active=demo_sites_active,
        campaigns_active=campaigns_active,
        emails_sent=emails_sent,
        emails_opened=emails_opened,
        emails_clicked=emails_clicked,
        open_rate=open_rate,
        click_rate=click_rate,
        orders_total=sales["total_orders"],
        sales_won=sales["won_count"],
        revenue_cents=sales["revenue_cents"],
        pipeline_cents=sales["pipeline_cents"],
        currency=sales["currency"],
    )


def _daily_counts(db: Session, uid: int, column, since: date) -> dict[str, int]:
    """Return a {YYYY-MM-DD: count} map of rows whose ``column`` day is >= ``since``."""
    day = func.date(column)
    rows = db.execute(
        select(day, func.count())
        .where(EmailLog.user_id == uid, column.isnot(None), day >= since)
        .group_by(day)
    ).all()
    return {str(d): int(c or 0) for d, c in rows}


@router.get("/activity", response_model=DashboardActivityResponse)
async def dashboard_activity(
    days: int = Query(default=14, ge=1, le=90),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DashboardActivityResponse:
    """Return the daily email activity (sent/opened/clicked) over the last ``days`` days."""
    uid = current_user.id
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)

    sent = _daily_counts(db, uid, EmailLog.sent_at, start)
    opened = _daily_counts(db, uid, EmailLog.opened_at, start)
    clicked = _daily_counts(db, uid, EmailLog.clicked_at, start)

    series: list[ActivityPoint] = []
    for offset in range(days):
        d = start + timedelta(days=offset)
        key = d.isoformat()
        series.append(
            ActivityPoint(
                date=key,
                sent=sent.get(key, 0),
                opened=opened.get(key, 0),
                clicked=clicked.get(key, 0),
            )
        )
    return DashboardActivityResponse(days=series)


@router.get("/hot-leads", response_model=HotLeadsResponse)
async def dashboard_hot_leads(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> HotLeadsResponse:
    """
    Return the hottest leads (demo + email engagement) for the current user.

    Behaviour aggregation depends on PostHog + DB reads; on any unexpected failure we
    return an empty list so the dashboard widget degrades gracefully instead of 500.
    """
    try:
        leads = await behavior_service.get_hot_leads(db, current_user.id, limit=20)
        items = [
            HotLeadResponse(
                prospect_id=lead["prospect_id"],
                name=lead.get("name") or "—",
                city=lead.get("city"),
                temperature=lead["temperature"],
                score=lead["score"],
                last_seen=str(lead["last_seen"]) if lead.get("last_seen") else None,
                signals=lead.get("signals", {}),
            )
            for lead in leads
        ]
    except Exception:  # noqa: BLE001
        logger.exception("hot-leads aggregation failed for user %s", current_user.id)
        return HotLeadsResponse(items=[])
    return HotLeadsResponse(items=items)
