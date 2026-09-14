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


class OrderBillingDetails(BaseModel):
    """Billing counterpart of an invoice, reviewed before it is issued.

    Pre-filled from the prospect, then edited by the operator: the address is
    mandatory provider-side, so a partial enrichment must be completable by hand.
    """

    name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    zip_code: str | None = Field(default=None, max_length=20)
    country_code: str = Field(default="FR", min_length=2, max_length=2)
    tax_id: str | None = Field(default=None, max_length=64)
    vat_number: str | None = Field(default=None, max_length=64)


class OrderBillingResponse(BaseModel):
    """Billing details pre-filled for the drawer (scraped values stay as-is).

    ``invoicing_provider`` drives which fields the drawer marks as required —
    ``None`` means a manual sale, where only a name and an email are needed.
    """

    name: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    zip_code: str | None = None
    country_code: str = "FR"
    tax_id: str | None = None
    vat_number: str | None = None
    invoicing_provider: str | None = None
    missing_fields: list[str] = Field(default_factory=list)


class OrderFinalizeRequest(BaseModel):
    """Payload of the « Finaliser la vente » drawer: reviewed billing + amount."""

    billing: OrderBillingDetails
    amount_cents: int = Field(ge=0)


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
    billing_address: str | None = None
    billing_city: str | None = None
    billing_zip_code: str | None = None
    billing_country_code: str | None = None
    billing_tax_id: str | None = None
    billing_vat_number: str | None = None
    stripe_payment_url: str | None = None
    payment_provider: str | None = None
    payment_url: str | None = None
    invoice_id: str | None = None
    invoice_number: str | None = None
    domain: str | None = None
    notes: str | None = None
    # Registrar order behind the go-live domain purchase (raw OVH status, labelled client-side).
    ovh_order_id: int | None = None
    ovh_order_status: str | None = None
    payment_link_sent_at: datetime | None = None
    paid_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    # Non-persisted: a follow-up warning for the drawer (e.g. site live but CMS not handed over).
    delivery_warning: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    """Paginated list of orders."""

    items: list[OrderResponse]
    total: int


class OrderPaymentEmailPreview(BaseModel):
    """Rendered payment-link email preview."""

    subject: str
    body_html: str


class OrderPaymentCheckResponse(BaseModel):
    """Result of reconciling an order against its provider."""

    newly_paid: bool
    order: OrderResponse


class OrderStatsResponse(BaseModel):
    """Commercial KPIs for the current user."""

    total_orders: int
    won_count: int
    pending_count: int
    revenue_cents: int
    pipeline_cents: int
    currency: str
