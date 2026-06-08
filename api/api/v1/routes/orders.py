"""Order / sales routes — available to every authenticated user."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User
from schemas.order import (
    OrderCreateRequest,
    OrderListResponse,
    OrderPaymentEmailPreview,
    OrderResponse,
    OrderStatsResponse,
    OrderUpdateRequest,
)
from services.auth_service import get_current_active_user
from services.order_service import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=OrderListResponse)
async def list_orders(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OrderListResponse:
    """List the current user's orders."""
    items = order_service.list_for_user(db, current_user.id)
    return OrderListResponse(
        items=[OrderResponse.model_validate(o) for o in items],
        total=len(items),
    )


@router.get("/stats", response_model=OrderStatsResponse)
async def order_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OrderStatsResponse:
    """Return commercial KPIs for the current user."""
    return OrderStatsResponse(**order_service.stats_for_user(db, current_user.id))


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Create a manual order (e.g. via "Marquer comme vendu")."""
    order = order_service.create(
        db,
        user_id=current_user.id,
        product_type=payload.product_type,
        prospect_id=payload.prospect_id,
        demo_site_id=payload.demo_site_id,
        amount_cents=payload.amount_cents,
        business_name=payload.business_name,
        customer_name=payload.customer_name,
        customer_email=str(payload.customer_email) if payload.customer_email else None,
        domain=payload.domain,
        notes=payload.notes,
    )
    return OrderResponse.model_validate(order)


def _get_order_or_404(db: Session, user_id: int, order_id: int):
    order = order_service.get_for_user(db, user_id, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Fetch a single order."""
    return OrderResponse.model_validate(_get_order_or_404(db, current_user.id, order_id))


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    payload: OrderUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Update an order's editable fields."""
    order = _get_order_or_404(db, current_user.id, order_id)
    updates = payload.model_dump(exclude_unset=True)
    if "customer_email" in updates and updates["customer_email"] is not None:
        updates["customer_email"] = str(updates["customer_email"])
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    order = order_service.update(db, order, updates)
    return OrderResponse.model_validate(order)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Cancel / delete an order."""
    order = _get_order_or_404(db, current_user.id, order_id)
    order_service.delete(db, order)


@router.post("/{order_id}/payment-link", response_model=OrderResponse)
async def create_order_payment_link(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Generate (or refresh) the Stripe payment link for an order."""
    order = _get_order_or_404(db, current_user.id, order_id)
    try:
        order = order_service.create_payment_link(db, order)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return OrderResponse.model_validate(order)


@router.get("/{order_id}/payment-email/preview", response_model=OrderPaymentEmailPreview)
async def preview_order_payment_email(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OrderPaymentEmailPreview:
    """Render the payment-link email so it can be reviewed before sending."""
    order = _get_order_or_404(db, current_user.id, order_id)
    rendered = order_service.build_payment_email(order, sender_name=current_user.name)
    return OrderPaymentEmailPreview(**rendered)


@router.post("/{order_id}/payment-email/send", response_model=OrderResponse)
async def send_order_payment_email(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Send the payment-link email to the client (creates the link if needed)."""
    order = _get_order_or_404(db, current_user.id, order_id)
    try:
        result = await order_service.send_payment_email(db, current_user, order)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.get("error", "Échec de l'envoi de l'email"),
        )
    db.refresh(order)
    return OrderResponse.model_validate(order)


@router.post("/{order_id}/mark-paid", response_model=OrderResponse)
async def mark_order_paid(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Manually mark an order as paid (phase 1 — before Stripe webhook)."""
    order = _get_order_or_404(db, current_user.id, order_id)
    order = order_service.mark_paid(db, order)
    await order_service.capture_sale_event(db, order.id)
    return OrderResponse.model_validate(order)


@router.post("/{order_id}/deploy", response_model=OrderResponse)
async def deploy_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Put the sold site online (Vercel + domain) and hand over CMS access."""
    order = _get_order_or_404(db, current_user.id, order_id)
    order = await order_service.fulfill_order(db, order)
    return OrderResponse.model_validate(order)
