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
from models.organization import OrganizationMember
from models.prospect_db import ProspectDB
from models.user import User
from schemas.dashboard import (
    ActivityPoint,
    CoverageCity,
    CoverageMember,
    CoverageResponse,
    DashboardActivityResponse,
    DashboardStatsResponse,
    HotLeadResponse,
    HotLeadsResponse,
)
from services.auth_service import get_current_active_user
from services.behavior_service import behavior_service
from services.order_service import order_service
from services.organization_service import organization_service

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


@router.get("/coverage", response_model=CoverageResponse)
async def dashboard_coverage(
    scope: str = Query("me", description="me | org | member"),
    member_id: int | None = Query(None, description="User id when scope=member"),
    categories: list[str] | None = Query(
        None, description="Optional trade filter (repeatable). Empty/absent = all trades."
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CoverageResponse:
    """
    Return prospect counts grouped by city for the prospection coverage map.

    Scope:
      - ``me``      → the current user's own prospects (default).
      - ``org``     → every prospect shared with the user's organization.
      - ``member``  → one org member's prospects (``member_id``), org-scoped so a
                      user can only inspect members of their own organization.

    ``categories`` filters by trade (``ProspectDB.category``, case-insensitive);
    absent or empty → all trades. ``available_categories`` always lists the
    distinct trades present in the SCOPE (ignoring the filter) so the frontend
    can build its trade selector from real values only.

    Cities are grouped case-insensitively; empty cities are excluded. The
    ``members`` list is filled only when the user belongs to an organization, so
    the frontend can offer a scope selector.
    """
    uid = current_user.id
    org_id = organization_service.user_org_id(db, uid)

    def scope_filter(stmt):  # noqa: ANN001, ANN202 — SQLAlchemy Select passthrough
        """Apply the resolved scope restriction to a prospect select."""
        if scope == "org" and org_id is not None:
            return stmt.where(ProspectDB.organization_id == org_id)
        if scope == "member" and member_id is not None and org_id is not None:
            # Guard: the member must belong to the caller's organization.
            return stmt.where(
                ProspectDB.user_id == member_id, ProspectDB.organization_id == org_id
            )
        return stmt.where(ProspectDB.user_id == uid)

    resolved_scope = scope
    if not (scope == "org" and org_id is not None) and not (
        scope == "member" and member_id is not None and org_id is not None
    ):
        resolved_scope = "me"

    city_col = func.trim(ProspectDB.city)
    stmt = select(
        func.min(city_col).label("city"),
        func.count().label("count"),
    ).where(city_col.isnot(None), city_col != "")
    stmt = scope_filter(stmt)

    wanted = [c.strip().lower() for c in (categories or []) if c and c.strip()]
    if wanted:
        stmt = stmt.where(func.lower(func.trim(ProspectDB.category)).in_(wanted))

    stmt = stmt.group_by(func.lower(city_col)).order_by(func.count().desc())
    rows = db.execute(stmt).all()
    cities = [CoverageCity(city=str(row.city), count=int(row.count)) for row in rows]
    total = sum(c.count for c in cities)

    # Distinct trades in the scope (unfiltered) — one small grouped query.
    cat_col = func.trim(ProspectDB.category)
    cat_stmt = scope_filter(
        select(func.min(cat_col).label("category"))
        .where(cat_col.isnot(None), cat_col != "")
        .group_by(func.lower(cat_col))
    )
    available_categories = sorted(
        (str(row.category) for row in db.execute(cat_stmt).all()), key=str.lower
    )

    members: list[CoverageMember] = []
    if org_id is not None:
        org = organization_service.get_user_organization(db, uid)
        if org is not None:
            member_rows = db.execute(
                select(User.id, User.name)
                .join(OrganizationMember, OrganizationMember.user_id == User.id)
                .where(OrganizationMember.organization_id == org_id)
                .order_by(User.name.asc())
            ).all()
            members = [CoverageMember(user_id=r.id, name=r.name) for r in member_rows]

    return CoverageResponse(
        scope=resolved_scope,
        cities=cities,
        total_prospects=total,
        members=members,
        available_categories=available_categories,
    )
