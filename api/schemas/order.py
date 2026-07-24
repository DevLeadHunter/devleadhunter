"""Pydantic schemas for orders / sales."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrderCreateRequest(BaseModel):
    """Payload to create a manual order."""

    product_type: str = Field(default="website", max_length=32)
    prospect_id: int | None = None
    demo_site_id: int | None = None
    amount_cents: int | None = Field(default=None, ge=0)
    business_name: str | None = Field(default=None, max_length=255)
    customer_name: str | None = Field(default=None, max_length=255)
    customer_email: EmailStr | None = None
    domain: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class OrderUpdateRequest(BaseModel):
    """Partial update of an order."""

    product_type: str | None = Field(default=None, max_length=32)
    amount_cents: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, max_length=32)
    business_name: str | None = Field(default=None, max_length=255)
    customer_name: str | None = Field(default=None, max_length=255)
    customer_email: EmailStr | None = None
    domain: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    demo_site_id: int | None = None
    prospect_id: int | None = None


class OrderResponse(BaseModel):
    """Order returned to the dashboard."""

    id: int
    product_type: str
    status: str
    prospect_id: int | None = None
    demo_site_id: int | None = None
    amount_cents: int
    currency: str
    business_name: str | None = None
    customer_name: str | None = None
    customer_email: str | None = None
    stripe_payment_url: str | None = None
    domain: str | None = None
    notes: str | None = None
    payment_link_sent_at: datetime | None = None
    paid_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


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
