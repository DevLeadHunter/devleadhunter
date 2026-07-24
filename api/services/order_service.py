"""
Order / sales orchestration.

Covers the end-of-tunnel: create a sale (manual for now), generate a Stripe
payment link, email it to the client (with preview), mark it paid (manually or
via the Stripe webhook), then fulfil it (deploy to prod + hand over CMS access).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from enums.order_status import WON_STATUSES, OrderStatus
from enums.product_type import PRODUCT_DEFAULT_AMOUNT_CENTS, PRODUCT_LABELS, ProductType
from models.order import Order
from models.prospect_db import ProspectDB
from models.user import User

if TYPE_CHECKING:
    from models.demo_site import DemoSite

logger = logging.getLogger(__name__)

# Post-payment fulfilment recovery bounds.
# A paid order that never went live is retried by the background recovery loop up to
# this many times, but only while it is recent enough (older ones need a human).
MAX_FULFILMENT_ATTEMPTS: int = 8
FULFILMENT_MAX_AGE_DAYS: int = 14
# Statuses that mean "paid but not yet fully delivered" → eligible for a retry.
_RETRYABLE_STATUSES: tuple[str, ...] = (OrderStatus.PAID.value, OrderStatus.DEPLOYING.value)
# Terminal states that must never be re-fulfilled.
_TERMINAL_STATUSES: tuple[str, ...] = (
    OrderStatus.DELIVERED.value,
    OrderStatus.REFUNDED.value,
    OrderStatus.CANCELLED.value,
)


def format_amount(amount_cents: int, currency: str = "eur") -> str:
    """Format an amount in cents as a human string (e.g. "500 €")."""
    symbol = "€" if (currency or "eur").lower() == "eur" else currency.upper()
    euros = amount_cents / 100
    text = f"{euros:.0f}" if euros == int(euros) else f"{euros:.2f}"
    return f"{text} {symbol}"


class OrderService:
    """Manage commercial orders scoped to a user."""

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    def list_for_user(self, db: Session, user_id: int) -> list[Order]:
        """List a user's orders, newest first."""
        return (
            db.query(Order)
            .filter(Order.user_id == user_id, Order.deleted_at.is_(None))
            .order_by(Order.created_at.desc())
            .all()
        )

    def get_for_user(self, db: Session, user_id: int, order_id: int) -> Order | None:
        """Fetch a user's order by id."""
        return (
            db.query(Order).filter(Order.id == order_id, Order.user_id == user_id, Order.deleted_at.is_(None)).first()
        )

    def get_by_id(self, db: Session, order_id: int) -> Order | None:
        """Fetch an order by id (used by webhook / fulfilment)."""
        return db.query(Order).filter(Order.id == order_id, Order.deleted_at.is_(None)).first()

    def get_by_payment_link_id(self, db: Session, payment_link_id: str) -> Order | None:
        """Resolve an order from a Stripe payment link id."""
        if not payment_link_id:
            return None
        return (
            db.query(Order).filter(Order.stripe_payment_link_id == payment_link_id, Order.deleted_at.is_(None)).first()
        )

    # ------------------------------------------------------------------ #
    # Mutations
    # ------------------------------------------------------------------ #

    def create(
        self,
        db: Session,
        *,
        user_id: int,
        product_type: str = ProductType.WEBSITE.value,
        prospect_id: int | None = None,
        demo_site_id: int | None = None,
        amount_cents: int | None = None,
        business_name: str | None = None,
        customer_name: str | None = None,
        customer_email: str | None = None,
        domain: str | None = None,
        notes: str | None = None,
    ) -> Order:
        """Create a manual order, pre-filling client info from the prospect when given."""
        if prospect_id and (not business_name or not customer_email):
            prospect = db.query(ProspectDB).filter(ProspectDB.id == prospect_id, ProspectDB.user_id == user_id).first()
            if prospect:
                business_name = business_name or prospect.name
                customer_email = customer_email or prospect.email

        resolved_amount = (
            amount_cents if amount_cents is not None else PRODUCT_DEFAULT_AMOUNT_CENTS.get(product_type, 50000)
        )

        order = Order(
            user_id=user_id,
            product_type=product_type,
            prospect_id=prospect_id,
            demo_site_id=demo_site_id,
            amount_cents=resolved_amount,
            currency="eur",
            business_name=business_name,
            customer_name=customer_name,
            customer_email=customer_email,
            domain=domain,
            notes=notes,
            status=OrderStatus.DRAFT.value,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    def update(self, db: Session, order: Order, updates: dict[str, Any]) -> Order:
        """Apply editable updates (amount, status, notes, domain, client info, links)."""
        editable = {
            "product_type",
            "amount_cents",
            "status",
            "business_name",
            "customer_name",
            "customer_email",
            "domain",
            "notes",
            "demo_site_id",
            "prospect_id",
        }
        for key, value in updates.items():
            if key in editable:
                setattr(order, key, value)
        db.commit()
        db.refresh(order)
        return order

    def delete(self, db: Session, order: Order) -> None:
        """Soft-delete an order and deactivate its Stripe payment link."""
        if order.stripe_payment_link_id:
            try:
                from services.stripe_payment_service import get_stripe_service

                service = get_stripe_service()
                if service:
                    service.deactivate_payment_link(order.stripe_payment_link_id)
            except Exception:
                logger.warning("Failed to deactivate payment link for order %s", order.id)
        order.deleted_at = datetime.now(UTC)
        order.status = OrderStatus.CANCELLED.value
        db.commit()

    # ------------------------------------------------------------------ #
    # Stripe payment link
    # ------------------------------------------------------------------ #

    def create_payment_link(self, db: Session, order: Order) -> Order:
        """Create (or refresh) the Stripe payment link for an order."""
        from services.stripe_payment_service import get_stripe_service

        service = get_stripe_service()
        if not service:
            raise ValueError("Stripe n'est pas configuré.")
        if not order.amount_cents or order.amount_cents <= 0:
            raise ValueError("Le montant de la commande doit être supérieur à 0.")

        result = service.create_order_payment_link(
            order_id=order.id,
            user_id=order.user_id,
            amount_cents=order.amount_cents,
            currency=order.currency,
            product_label=PRODUCT_LABELS.get(order.product_type, "Site web"),
            business_name=order.business_name,
        )
        order.stripe_payment_link_id = result["payment_link_id"]
        order.stripe_payment_url = result["url"]
        if order.status == OrderStatus.DRAFT.value:
            order.status = OrderStatus.PAYMENT_PENDING.value
        db.commit()
        db.refresh(order)
        return order

    # ------------------------------------------------------------------ #
    # Payment-link email (with preview)
    # ------------------------------------------------------------------ #

    def build_payment_email(self, order: Order, sender_name: str) -> dict[str, str]:
        """Render the subject + HTML body of the payment-link email for an order."""
        business = order.business_name or "votre entreprise"
        amount = format_amount(order.amount_cents, order.currency)
        product = PRODUCT_LABELS.get(order.product_type, "site web")
        url = order.stripe_payment_url or "#"

        subject = f"Votre {product} est prêt — finalisons ensemble"
        body_html = f"""
        <div style="font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color:#1a1a1a; max-width:560px; margin:0 auto;">
          <p>Bonjour,</p>
          <p>
            Comme convenu, le <strong>{product}</strong> de <strong>{business}</strong> est prêt.
            Pour le mettre en ligne sur votre nom de domaine et vous transmettre vos accès,
            il vous suffit de finaliser le paiement unique de <strong>{amount}</strong> (pas d'abonnement, site à vie).
          </p>
          <p style="text-align:center; margin:32px 0;">
            <a href="{url}" style="background:#0284c7; color:#ffffff; text-decoration:none; padding:14px 28px; border-radius:8px; font-weight:600; display:inline-block;">
              Régler {amount} en ligne
            </a>
          </p>
          <p style="font-size:13px; color:#555;">
            Paiement sécurisé par Stripe. Dès réception, je mets votre site en ligne et je vous envoie vos identifiants
            pour gérer vous-même votre contenu.
          </p>
          <p>Une question avant de valider ? Répondez simplement à cet email.</p>
          <p>Bien à vous,<br/>{sender_name}</p>
        </div>
        """.strip()
        return {"subject": subject, "body_html": body_html}

    async def send_payment_email(self, db: Session, user: User, order: Order) -> dict[str, Any]:
        """Send the payment-link email to the client via the user's active sending identity."""
        if not order.customer_email:
            raise ValueError("Aucune adresse email client sur la commande.")
        if not order.stripe_payment_url:
            self.create_payment_link(db, order)

        from services.email_sending_service import EmailSendingService

        rendered = self.build_payment_email(order, sender_name=user.name)
        sending = EmailSendingService(db)
        result = await sending.send_via_user_identity(
            user_id=user.id,
            recipient_email=order.customer_email,
            recipient_name=order.customer_name or order.business_name,
            subject=rendered["subject"],
            body_html=rendered["body_html"],
            prospect_id=str(order.prospect_id) if order.prospect_id else None,
        )
        if result.get("success"):
            order.payment_link_sent_at = datetime.now(UTC)
            if order.status == OrderStatus.DRAFT.value:
                order.status = OrderStatus.PAYMENT_PENDING.value
            db.commit()
            db.refresh(order)
        return result

    # ------------------------------------------------------------------ #
    # Payment confirmation + fulfilment
    # ------------------------------------------------------------------ #

    def mark_paid(
        self,
        db: Session,
        order: Order,
        *,
        stripe_session_id: str | None = None,
        stripe_payment_intent_id: str | None = None,
    ) -> Order:
        """Mark an order as paid (manual or webhook). Idempotent."""
        if order.paid_at:
            return order
        order.paid_at = datetime.now(UTC)
        order.status = OrderStatus.PAID.value
        if stripe_session_id:
            order.stripe_session_id = stripe_session_id
        if stripe_payment_intent_id:
            order.stripe_payment_intent_id = stripe_payment_intent_id
        db.commit()
        db.refresh(order)
        return order

    def mark_refunded(self, db: Session, order: Order) -> Order:
        """Mark an order as refunded (manual or Stripe webhook). Idempotent."""
        if order.status == OrderStatus.REFUNDED.value:
            return order
        order.status = OrderStatus.REFUNDED.value
        order.refunded_at = datetime.now(UTC)
        db.commit()
        db.refresh(order)
        return order

    async def capture_sale_event(self, db: Session, order_id: int) -> None:
        """
        Push a ``sale`` event to PostHog (best-effort) so it closes the funnel
        email → démo → vente. distinct_id = the prospect's demo slug (same identity
        as the email/demo events).
        """
        from services.posthog_service import posthog_service

        if not posthog_service.can_capture:
            return
        order = self.get_by_id(db, order_id)
        if not order:
            return

        slug: str | None = None
        if order.demo_site_id:
            from models.demo_site import DemoSite

            site = db.query(DemoSite).filter(DemoSite.id == order.demo_site_id).first()
            slug = site.slug if site else None
        distinct_id = slug or (f"prospect_{order.prospect_id}" if order.prospect_id else f"order_{order.id}")
        await posthog_service.capture(
            distinct_id=distinct_id,
            event="sale",
            properties={
                "amount_cents": order.amount_cents,
                "currency": order.currency,
                "product_type": order.product_type,
                "prospect_id": order.prospect_id,
                "demo_slug": slug,
                "order_id": order.id,
            },
        )

    def get_by_payment_intent_id(self, db: Session, payment_intent_id: str) -> Order | None:
        """Resolve an order from a Stripe payment intent id."""
        if not payment_intent_id:
            return None
        return (
            db.query(Order)
            .filter(Order.stripe_payment_intent_id == payment_intent_id, Order.deleted_at.is_(None))
            .first()
        )

    def try_mark_paid_from_event(self, db: Session, event: dict[str, Any]) -> int | None:
        """
        If a Stripe event is an order payment, mark the order paid and return its id.

        Returns None when the event is not an order payment (e.g. a credits purchase),
        so the caller can fall back to the credits handler.
        """
        if event.get("type") != "checkout.session.completed":
            return None
        session = event.get("data", {}).get("object", {})
        if session.get("payment_status") not in ("paid", "no_payment_required"):
            return None

        metadata = session.get("metadata", {}) or {}
        order: Order | None = None
        if metadata.get("type") == "order" and metadata.get("order_id"):
            order = self.get_by_id(db, int(metadata["order_id"]))
        if order is None:
            payment_link = session.get("payment_link")
            link_id = payment_link.get("id") if isinstance(payment_link, dict) else payment_link
            if link_id:
                order = self.get_by_payment_link_id(db, str(link_id))

        if order is None:
            return None

        payment_intent = session.get("payment_intent")
        intent_id = payment_intent.get("id") if isinstance(payment_intent, dict) else payment_intent
        self.mark_paid(
            db,
            order,
            stripe_session_id=session.get("id"),
            stripe_payment_intent_id=str(intent_id) if intent_id else None,
        )
        return order.id

    def try_handle_refund_from_event(self, db: Session, event: dict[str, Any]) -> int | None:
        """
        If a Stripe event is a refund, mark the matching order refunded.

        Handles ``charge.refunded`` and ``refund.created`` / ``refund.updated``.
        Returns the order id when handled, else None (so the caller can fall back).
        """
        event_type = event.get("type", "")
        if event_type not in ("charge.refunded", "refund.created", "refund.updated"):
            return None

        obj = event.get("data", {}).get("object", {})
        # charge.refunded → object is a Charge (has payment_intent + refunded flag)
        # refund.* → object is a Refund (has payment_intent + status)
        payment_intent = obj.get("payment_intent")
        intent_id = payment_intent.get("id") if isinstance(payment_intent, dict) else payment_intent
        if not intent_id:
            return None

        if event_type.startswith("refund.") and obj.get("status") not in ("succeeded", None):
            return None

        order = self.get_by_payment_intent_id(db, str(intent_id))
        if order is None:
            return None

        self.mark_refunded(db, order)
        return order.id

    async def _verify_delivery(self, order: Order, demo_site: DemoSite) -> tuple[bool, str]:
        """
        Verify the client truly has a working site on their domain AND CMS access.

        Returns ``(ok, message)``. ``ok`` is True only when the custom domain
        serves a page (HTTP < 400) and the Storyblok CMS handover is real — a
        space exists and the invite was sent (not mock mode).

        Args:
            order: The paid order being fulfilled (provides the domain).
            demo_site: The linked demo site (provides CMS state).

        Returns:
            Tuple of (delivered_ok, human-readable reason).
        """
        from services.demo_site_verification_service import demo_site_verification_service

        problems: list[str] = []

        if not order.domain:
            domain_live = False
            problems.append("aucun domaine défini")
        else:
            domain_live = await demo_site_verification_service.check_domain_live(order.domain)
            if not domain_live:
                problems.append(f"le domaine {order.domain} ne répond pas encore (DNS/Vercel)")

        cms_ready: bool = bool(demo_site.storyblok_space_id) and bool(demo_site.storyblok_invite_sent)
        if not cms_ready:
            if not demo_site.storyblok_space_id:
                problems.append("espace CMS Storyblok non créé (mode mock ?)")
            else:
                problems.append("invitation CMS non envoyée au client")

        if domain_live and cms_ready:
            return True, "Site en ligne sur le domaine client et accès CMS transmis."
        return False, "Livraison incomplète : " + " ; ".join(problems)

    async def fulfill_order_async(self, order_id: int) -> None:
        """
        One tracked fulfilment attempt in its own DB session (safe for background tasks):
        deploy the site to prod (Vercel + domain) and hand over CMS access.

        Increments ``fulfillment_attempts`` and records ``fulfillment_last_error`` so a
        paid-but-undelivered order is retried by the recovery loop (bounded) instead of
        silently stuck. Terminal orders (delivered/refunded/cancelled) are skipped.
        """
        from core.database import SessionLocal

        db = SessionLocal()
        try:
            order = self.get_by_id(db, order_id)
            if not order or order.product_type != ProductType.WEBSITE.value:
                return
            if order.status in _TERMINAL_STATUSES:
                return

            order.fulfillment_attempts = (order.fulfillment_attempts or 0) + 1
            order.fulfillment_last_error = None
            db.commit()

            try:
                await self.fulfill_order(db, order)
            except Exception as exc:
                logger.exception("Order fulfilment attempt failed for order_id=%s", order_id)
                order = self.get_by_id(db, order_id)
                if order is not None:
                    order.fulfillment_last_error = str(exc)[:500]
                    db.commit()
        finally:
            db.close()

    def list_stuck_fulfilment_order_ids(self, db: Session) -> list[int]:
        """
        Ids of website orders that were paid but never fully delivered and are still
        within the auto-retry budget (attempts + age). Consumed by the recovery loop.

        Args:
            db: Database session.

        Returns:
            The order ids to retry.
        """
        cutoff: datetime = datetime.now(UTC) - timedelta(days=FULFILMENT_MAX_AGE_DAYS)
        rows = (
            db.query(Order.id)
            .filter(
                Order.product_type == ProductType.WEBSITE.value,
                Order.status.in_(_RETRYABLE_STATUSES),
                Order.deleted_at.is_(None),
                Order.fulfillment_attempts < MAX_FULFILMENT_ATTEMPTS,
                Order.created_at >= cutoff,
            )
            .all()
        )
        return [row[0] for row in rows]

    async def fulfill_order(self, db: Session, order: Order) -> Order:
        """Deploy the linked demo site to prod and hand over Storyblok access."""
        from models.demo_site import DemoSite
        from services.demo_site_service import demo_site_service

        if not order.demo_site_id:
            logger.info("Order %s has no linked demo site — skipping deploy", order.id)
            return order

        demo_site = (
            db.query(DemoSite).filter(DemoSite.id == order.demo_site_id, DemoSite.user_id == order.user_id).first()
        )
        if not demo_site:
            return order

        order.status = OrderStatus.DEPLOYING.value
        db.commit()

        # 1) Deploy to production (Vercel + domain) — best effort.
        try:
            from services.vercel_service import vercel_service

            await vercel_service.deploy_demo_site(db, demo_site, domain=order.domain)
        except Exception:
            logger.exception("Vercel deployment failed for order_id=%s", order.id)

        # 2) Take the demo offline (demo.dibodev.fr 404) and promote the site to
        #    the client's production domain (served via host→slug, permanent).
        if order.domain:
            try:
                await demo_site_service.mark_delivered(db, demo_site, order.domain)
            except Exception:
                logger.warning("mark_delivered failed for order_id=%s", order.id, exc_info=True)

        # 3) Hand over CMS access (Storyblok invite) now that the sale is closed.
        try:
            if not demo_site.storyblok_invite_sent:
                await demo_site_service.invite_client_to_cms(db, demo_site)
        except Exception:
            logger.warning("Storyblok handover failed for order_id=%s", order.id, exc_info=True)

        db.refresh(demo_site)

        # 4) Only declare the order delivered once the client truly has a working
        #    site on their domain AND real CMS access. Otherwise keep it DEPLOYING
        #    with a reason — the operator fixes DNS/CMS and re-runs
        #    POST /orders/{id}/deploy to re-verify.
        delivered_ok, message = await self._verify_delivery(order, demo_site)
        demo_site.verification_message = message
        if delivered_ok:
            order.status = OrderStatus.DELIVERED.value
            order.delivered_at = datetime.now(UTC)
        else:
            order.status = OrderStatus.DEPLOYING.value
            logger.warning("Order %s kept in DEPLOYING — %s", order.id, message)
        db.commit()
        db.refresh(order)
        return order

    # ------------------------------------------------------------------ #
    # Commercial tracking
    # ------------------------------------------------------------------ #

    def stats_for_user(self, db: Session, user_id: int, since: datetime | None = None) -> dict[str, Any]:
        """Aggregate sales KPIs for a user (counts + revenue).

        Args:
            db: Database session.
            user_id: Owner of the orders.
            since: When set, only count orders created after this moment
                (drives the dashboard period filter).
        """
        orders = self.list_for_user(db, user_id)
        if since is not None:
            orders = [o for o in orders if o.created_at is not None and o.created_at >= since]
        won = [o for o in orders if o.status in WON_STATUSES]
        revenue_cents = sum(o.amount_cents for o in won)
        pending = [o for o in orders if o.status == OrderStatus.PAYMENT_PENDING.value]
        pipeline_cents = sum(o.amount_cents for o in pending)
        return {
            "total_orders": len(orders),
            "won_count": len(won),
            "pending_count": len(pending),
            "revenue_cents": revenue_cents,
            "pipeline_cents": pipeline_cents,
            "currency": "eur",
        }


order_service = OrderService()
