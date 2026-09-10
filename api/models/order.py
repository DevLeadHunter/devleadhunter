"""Order model — a sale of a product (website, …) to a prospect/client."""

from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from enums.order_status import OrderStatus
from enums.product_type import ProductType


class Order(Base):
    """A commercial order, scoped to the user who owns it."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    prospect_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    demo_site_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    product_type: Mapped[str] = mapped_column(String(32), nullable=False, default=ProductType.WEBSITE.value, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=OrderStatus.DRAFT.value, index=True)

    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=50000)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="eur")

    # Denormalized client info (filled from the prospect, editable for display/email)
    business_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Billing address of the invoiced client, reviewed by the operator before the
    # invoice is issued: Qonto rejects a client without a valid postal address,
    # and enrichment only yields a free-form street line.
    billing_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    billing_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    billing_zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    billing_country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    billing_tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    billing_vat_number: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Stripe payment artifacts (legacy path — still written by the credits webhook
    # and pre-existing orders; superseded by the provider-agnostic columns below)
    stripe_payment_link_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    stripe_payment_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    stripe_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    refunded_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Provider-agnostic payment/invoice artifacts (Qonto or Stripe, per the user's
    # connected PaymentAccount). The provider issues the invoice and owns numbering.
    payment_provider: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    payment_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    invoice_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Attached payment-link id (Qonto): its status flags a card/Apple Pay payment before settlement.
    payment_link_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Deployment / delivery
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    payment_link_sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Post-payment fulfilment retry tracking (background recovery loop). Guard against
    # the fire-and-forget gap: a paid order that never went live is retried, capped,
    # and its last error kept for the operator.
    fulfillment_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    fulfillment_last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.utcnow, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<Order id={self.id} product={self.product_type} status={self.status} amount={self.amount_cents}>"
