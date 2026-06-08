"""Order model — a sale of a product (website, …) to a prospect/client."""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.database import Base
from enums.order_status import OrderStatus
from enums.product_type import ProductType


class Order(Base):
    """A commercial order, scoped to the user who owns it."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    prospect_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    demo_site_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    product_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ProductType.WEBSITE.value, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=OrderStatus.DRAFT.value, index=True
    )

    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=50000)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="eur")

    # Denormalized client info (filled from the prospect, editable for display/email)
    business_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Stripe payment artifacts
    stripe_payment_link_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    stripe_payment_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stripe_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    refunded_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Deployment / delivery
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    payment_link_sent_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now(), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<Order id={self.id} product={self.product_type} status={self.status} amount={self.amount_cents}>"
