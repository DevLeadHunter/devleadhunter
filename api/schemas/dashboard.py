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
