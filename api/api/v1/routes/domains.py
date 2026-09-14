"""Domain routes — suggest a ``.fr`` for a prospect and check availability.

Both endpoints are credential-free (AFNIC RDAP + Groq): they power the "pre-filled,
ideally-available domain" step of the post-sale go-live. The actual registration + DNS
(per-user ``DomainProvider``) come in a later increment, gated on the operator's OVH keys.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from models.prospect_db import ProspectDB
from models.user import User
from services.auth_service import require_auth, require_super_admin
from services.domain.availability import is_available
from services.domain.ovh_catalog import price_for_domain
from services.domain.ovh_provider import DomainProviderError, ovh_domain_provider
from services.domain.provision_service import domain_provision_service
from services.domain.suggestion_service import domain_suggestion_service
from services.order_service import order_service
from services.organization_service import organization_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/domains", tags=["domains"])


class DomainAvailability(BaseModel):
    """Availability + real first-year price for one domain."""

    domain: str = Field(..., description="Full domain, e.g. « tacos-maru.fr »")
    available: bool | None = Field(..., description="True = free, False = taken, null = could not check")
    price_eur: float | None = Field(..., description="OVH first-year price (TTC), null when OVH does not sell the TLD")


class DomainSuggestionsResponse(BaseModel):
    """The best pre-fill plus every candidate considered."""

    suggested: str | None = Field(..., description="Best domain to pre-fill, null when none could be built")
    candidates: list[DomainAvailability] = Field(default_factory=list, description="All candidates, best first")


def _normalize_domain(name: str) -> str:
    """Clean raw input to a full domain, defaulting to ``.fr`` when the operator typed no TLD.

    « chezmimon » → « chezmimon.fr » ; « chezmimon.com » stays « chezmimon.com ».
    """
    cleaned = (name or "").strip().lower().strip(".")
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nom de domaine vide")
    domain = cleaned if "." in cleaned else f"{cleaned}.fr"
    if not domain.split(".")[0]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nom de domaine invalide")
    return domain


@router.get(
    "/availability",
    response_model=DomainAvailability,
    summary="Check whether a domain is free, with its real price",
    description="Query RDAP (AFNIC for .fr, the bootstrap otherwise) + the OVH catalog for the real TLD price.",
)
async def check_availability(name: str, current_user: User = Depends(require_auth)) -> DomainAvailability:
    """Return the availability + real first-year price of one domain (best-effort)."""
    del current_user
    domain = _normalize_domain(name)
    return DomainAvailability(
        domain=domain,
        available=await is_available(domain),
        price_eur=await price_for_domain(domain),
    )


@router.get(
    "/suggestions",
    response_model=DomainSuggestionsResponse,
    summary="Suggest a .fr domain from a prospect or a business name",
    description="Build logical .fr candidates (name/city/trade), enrich with AI, check availability. Pass prospect_id, or name.",
)
async def suggest_domains(
    prospect_id: int | None = None,
    name: str | None = None,
    city: str | None = None,
    category: str | None = None,
    ai: bool = True,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> DomainSuggestionsResponse:
    """Suggest a pre-fillable ``.fr`` domain from a visible prospect or a raw business name.

    Pass ``ai=false`` for snappy as-you-type suggestions (skips Groq).

    Raises:
        HTTPException: 404 when a given prospect is not visible; 400 when neither prospect_id nor name is given.
    """
    if prospect_id is not None:
        # Visibility: the prospect must belong to the caller or their organization (no cross-org leak).
        row = db.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prospect {prospect_id} not found")
        if row.user_id != current_user.id:
            org_id = organization_service.user_org_id(db, current_user.id)
            if org_id is None or row.organization_id != org_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prospect {prospect_id} not found")
        name, city, category = row.name, row.city, row.category
    if not (name or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="prospect_id ou name requis")

    suggestion = await domain_suggestion_service.suggest(name=name, city=city, category=category, use_ai=ai)
    return DomainSuggestionsResponse(
        suggested=suggestion.suggested,
        candidates=[
            DomainAvailability(domain=c.domain, available=c.available, price_eur=c.price_eur)
            for c in suggestion.candidates
        ],
    )


class RegistrarStatus(BaseModel):
    """Whether the OVH registrar is wired, and which account it points at."""

    configured: bool = Field(..., description="True when the OVH credentials are present")
    account: str | None = Field(None, description="OVH account id (nichandle) when the signed check succeeds")


class DomainActionRequest(BaseModel):
    """Payload naming a single .fr domain for a registrar action."""

    domain: str = Field(..., description="Full .fr domain, e.g. « tacos-maru.fr »")


@router.get(
    "/registrar-status",
    response_model=RegistrarStatus,
    summary="Check the OVH registrar connection (no spend)",
    description="Super-admin. Does a signed GET /me to prove the keys + signature work, without ordering anything.",
)
async def registrar_status(current_user: User = Depends(require_super_admin)) -> RegistrarStatus:
    """Return whether OVH is configured and reachable (a safe, no-spend auth check)."""
    del current_user
    if not ovh_domain_provider.is_configured:
        return RegistrarStatus(configured=False, account=None)
    return RegistrarStatus(configured=True, account=await ovh_domain_provider.account_id())


class DomainProvisionRequest(BaseModel):
    """Payload to buy a domain and bring a paid sale's site online."""

    domain: str = Field(..., description="Full domain to register, e.g. « devleadhunter.fr »")
    order_id: int | None = Field(
        None, description="When given, the domain is saved on that sale and its linked demo is deployed to it"
    )


class DomainRegisterResult(BaseModel):
    """Outcome of a registrar purchase."""

    domain: str = Field(..., description="The domain ordered")
    ovh_order_id: int | None = Field(None, description="OVH order id, when returned")


@router.post(
    "/provision",
    response_model=DomainRegisterResult,
    summary="Buy the domain and put the paid sale's site online (register + DNS + deploy)",
    description="Super-admin, one action. Registers the domain (spends money), points its DNS to Vercel, and — when order_id is given — deploys the sale's linked demo to it.",
)
async def provision_domain(
    request: DomainProvisionRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> DomainRegisterResult:
    """Register a domain and, for a paid sale, deploy its linked site to it. Super-admin only.

    Raises:
        HTTPException: 404 when the order is not visible, 503 when OVH is not configured, 502 when the order fails.
    """
    domain = _normalize_domain(request.domain)
    if not ovh_domain_provider.is_configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OVH n'est pas configuré")

    sale = None
    if request.order_id is not None:
        sale = order_service.get_for_user(db, current_user.id, request.order_id)
        if sale is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vente {request.order_id} introuvable")
        sale.domain = domain
        db.commit()

    try:
        ovh_order = await domain_provision_service.provision(domain, user_id=current_user.id)
    except DomainProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    # Deploy the sale's linked demo onto the freshly-ordered domain (best-effort — DNS lands in the background).
    if sale is not None:
        # Keep the registrar order on the sale so the fulfilment loop can follow its status.
        ovh_order_id = ovh_order.get("orderId")
        if isinstance(ovh_order_id, int):
            sale.ovh_order_id = ovh_order_id
            sale.ovh_order_status = None
            db.commit()
        try:
            await order_service.fulfill_order(db, sale)
        except Exception:
            # Deployment is best-effort; the domain order already succeeded, so don't fail the call.
            logger.warning("fulfill_order failed after provisioning domain for order %s", sale.id, exc_info=True)

    return DomainRegisterResult(domain=domain, ovh_order_id=ovh_order.get("orderId"))


@router.post(
    "/register",
    response_model=DomainRegisterResult,
    summary="Buy a .fr domain on the operator's OVH account (spends money)",
    description="Super-admin fallback. Registration is async at OVH — point the DNS once the domain is active.",
)
async def register_domain(
    request: DomainActionRequest,
    current_user: User = Depends(require_super_admin),
) -> DomainRegisterResult:
    """Register a ``.fr`` domain via OVH (real purchase). Super-admin only.

    Raises:
        HTTPException: 503 when OVH is not configured, 502 when the OVH order fails.
    """
    del current_user
    domain = _normalize_domain(request.domain)
    if not ovh_domain_provider.is_configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OVH n'est pas configuré")
    try:
        order = await ovh_domain_provider.register(domain)
    except DomainProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return DomainRegisterResult(domain=domain, ovh_order_id=order.get("orderId"))


@router.post(
    "/point-dns",
    summary="Point a domain's apex DNS at the Vercel demo-host",
    description="Super-admin. Run once the domain is active at OVH (registration is async).",
)
async def point_domain_dns(
    request: DomainActionRequest,
    current_user: User = Depends(require_super_admin),
) -> dict[str, str]:
    """Set the domain's apex ``A`` record to Vercel and refresh the zone. Super-admin only.

    Raises:
        HTTPException: 503 when OVH is not configured, 502 when the DNS update fails.
    """
    del current_user
    domain = _normalize_domain(request.domain)
    if not ovh_domain_provider.is_configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OVH n'est pas configuré")
    try:
        await ovh_domain_provider.point_to_vercel(domain)
    except DomainProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return {"status": "ok", "domain": domain}
