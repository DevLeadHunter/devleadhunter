"""Pydantic schemas for the dashboard home KPIs."""
from typing import Any, Optional

from pydantic import BaseModel, Field


class DashboardStatsResponse(BaseModel):
    """Aggregated KPIs shown on the dashboard home page."""

    prospects_total: int
    demo_sites_active: int
    campaigns_active: int
    emails_sent: int
    emails_opened: int
    emails_clicked: int
    open_rate: float
    click_rate: float
    orders_total: int
    sales_won: int
    revenue_cents: int
    pipeline_cents: int
    currency: str


class HotLeadResponse(BaseModel):
    """A hot/warm lead surfaced on the dashboard (demo + email engagement)."""

    prospect_id: int
    name: str
    city: Optional[str] = None
    temperature: str
    score: int
    last_seen: Optional[str] = None
    signals: dict[str, Any] = Field(default_factory=dict)


class HotLeadsResponse(BaseModel):
    """List of hot leads for the dashboard widget."""

    items: list[HotLeadResponse]


class ActivityPoint(BaseModel):
    """Email activity counters for a single day."""

    date: str
    sent: int
    opened: int
    clicked: int


class DashboardActivityResponse(BaseModel):
    """Daily email activity series for the dashboard trend chart."""

    days: list[ActivityPoint]


class CoverageCity(BaseModel):
    """Prospect count for one city (coverage map)."""

    city: str
    count: int


class CoverageMember(BaseModel):
    """An organization member selectable as a coverage scope."""

    user_id: int
    name: str


class CoverageProspectRow(BaseModel):
    """Light prospect recap for the coverage zone drawer (kept airy on purpose)."""

    id: int
    name: str
    city: Optional[str] = None
    category: Optional[str] = None
    has_demo: bool = False
    emails_sent: int = 0
    emails_opened: int = 0
    emails_clicked: int = 0
    is_sold: bool = False


class CoverageProspectsResponse(BaseModel):
    """Prospects of a coverage zone (one or several cities)."""

    items: list[CoverageProspectRow]
    total: int


class CoverageResponse(BaseModel):
    """Prospection coverage aggregated by city, for the selected scope."""

    scope: str
    cities: list[CoverageCity]
    total_prospects: int
    # Populated only when the user belongs to an organization (scope selector).
    members: list[CoverageMember] = Field(default_factory=list)
    # Distinct trades (ProspectDB.category) present in the SCOPE, ignoring the
    # ``categories`` filter — feeds the trade multi-select without ghost values.
    available_categories: list[str] = Field(default_factory=list)
