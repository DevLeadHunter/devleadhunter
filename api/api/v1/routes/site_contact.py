"""
Contact page of the marketing site: a visitor's message is mailed to the publisher.

Public by design (asking a question needs no account), so each visitor is rate limited and a hidden honeypot
field drops bots without telling them.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from api.v1.routes.ai_assistant_common import client_ip
from core.database import get_db
from schemas.site_contact import SiteContactRequest, SiteContactResponse
from services.rate_limiter import site_contact_limiter
from services.site_contact_service import SiteContactDeliveryError, site_contact_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post("", response_model=SiteContactResponse)
async def send_contact_message(
    payload: SiteContactRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> SiteContactResponse:
    """
    Mail a visitor's message to the publisher.

    Args:
        payload: The visitor's message.
        request: The HTTP request, read for the visitor's address.
        db: Active database session.

    Returns:
        The confirmation that the message is on its way.

    Raises:
        HTTPException: 429 when the visitor sent too many messages, 503 when the message could not be mailed.
    """
    if not site_contact_limiter.allow(f"contact:{client_ip(request)}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de messages envoyés, réessayez dans une heure.",
        )
    if payload.website:
        logger.info("Contact page honeypot filled, message dropped")
        return SiteContactResponse()
    try:
        await site_contact_service.send(db, payload)
    except SiteContactDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le message n'est pas parti, réessayez dans un instant.",
        ) from exc
    return SiteContactResponse()
