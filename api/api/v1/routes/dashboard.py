"""Dashboard home KPIs aggregated for the current user."""
from fastapi import APIRouter, Depends
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from models.campaign import Campaign, CampaignStatus
from models.demo_site import DemoSite
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from models.user import User
from schemas.dashboard import DashboardStatsResponse, HotLeadResponse, HotLeadsResponse
from services.auth_service import get_current_active_user
from services.behavior_service import behavior_service
from services.order_service import order_service

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


@router.get("/hot-leads", response_model=HotLeadsResponse)
async def dashboard_hot_leads(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> HotLeadsResponse:
    """Return the hottest leads (demo + email engagement) for the current user."""
    leads = await behavior_service.get_hot_leads(db, current_user.id, limit=20)
    return HotLeadsResponse(
        items=[
            HotLeadResponse(
                prospect_id=lead["prospect_id"],
                name=lead["name"],
                city=lead.get("city"),
                temperature=lead["temperature"],
                score=lead["score"],
                last_seen=str(lead["last_seen"]) if lead.get("last_seen") else None,
                signals=lead.get("signals", {}),
            )
            for lead in leads
        ]
    )
