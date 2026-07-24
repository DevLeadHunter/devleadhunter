"""Lifecycle status of a sale / order."""

from enum import Enum


class OrderStatus(str, Enum):
    """Commercial lifecycle of an order."""

    DRAFT = "draft"  # created, no payment link yet
    PAYMENT_PENDING = "payment_pending"  # payment link generated / email sent
    PAID = "paid"  # client paid (manual mark or Stripe webhook)
    DEPLOYING = "deploying"  # going live on Vercel + domain
    DELIVERED = "delivered"  # site online + CMS access handed over
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


# Statuses that count as a closed/won sale for commercial tracking.
WON_STATUSES: tuple[str, ...] = (
    OrderStatus.PAID.value,
    OrderStatus.DEPLOYING.value,
    OrderStatus.DELIVERED.value,
)
