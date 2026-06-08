"""Pydantic schemas for orders / sales."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class OrderCreateRequest(BaseModel):
    """Payload to create a manual order."""

    product_type: str = Field(default="website", max_length=32)
    prospect_id: Optional[int] = None
    demo_site_id: Optional[int] = None
    amount_cents: Optional[int] = Field(default=None, ge=0)
    business_name: Optional[str] = Field(default=None, max_length=255)
    customer_name: Optional[str] = Field(default=None, max_length=255)
    customer_email: Optional[EmailStr] = None
    domain: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


class OrderUpdateRequest(BaseModel):
    """Partial update of an order."""

    product_type: Optional[str] = Field(default=None, max_length=32)
    amount_cents: Optional[int] = Field(default=None, ge=0)
    status: Optional[str] = Field(default=None, max_length=32)
    business_name: Optional[str] = Field(default=None, max_length=255)
    customer_name: Optional[str] = Field(default=None, max_length=255)
    customer_email: Optional[EmailStr] = None
    domain: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None
    demo_site_id: Optional[int] = None
    prospect_id: Optional[int] = None


class OrderResponse(BaseModel):
    """Order returned to the dashboard."""

    id: int
    product_type: str
    status: str
    prospect_id: Optional[int] = None
    demo_site_id: Optional[int] = None
    amount_cents: int
    currency: str
    business_name: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    stripe_payment_url: Optional[str] = None
    domain: Optional[str] = None
    notes: Optional[str] = None
    payment_link_sent_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    """Paginated list of orders."""

    items: list[OrderResponse]
    total: int


class OrderPaymentEmailPreview(BaseModel):
    """Rendered payment-link email preview."""

    subject: str
    body_html: str


class OrderStatsResponse(BaseModel):
    """Commercial KPIs for the current user."""

    total_orders: int
    won_count: int
    pending_count: int
    revenue_cents: int
    pipeline_cents: int
    currency: str
