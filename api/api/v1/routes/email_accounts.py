"""
Email accounts routes for managing user's email sender configurations.
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from core.config import settings
from core.database import get_db
from models.user import User
from models.email_account import EmailAccount
from schemas.email_account import (
    EmailAccountCreateCustomDomain,
    EmailAccountUpdate,
    EmailAccountResponse,
    DNSVerificationResponse
)
from services.auth_service import get_current_user
from services.dns_service import sending_domain_dns_service
from services.gmail_oauth_service import GmailOAuthService
from services.encryption_service import encryption_service
from enums.email_account_type import EmailAccountType
import json

router = APIRouter(prefix="/email-accounts", tags=["email-accounts"])
logger = logging.getLogger(__name__)


@router.get("", response_model=List[EmailAccountResponse])
async def get_email_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all email accounts for the current user.
    """
    stmt = select(EmailAccount).where(
        EmailAccount.user_id == current_user.id
    ).order_by(EmailAccount.is_default.desc(), EmailAccount.created_at.desc())
    
    result = db.execute(stmt)
    accounts = result.scalars().all()
    
    return accounts


@router.get("/{account_id}", response_model=EmailAccountResponse)
async def get_email_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific email account by ID.
    """
    stmt = select(EmailAccount).where(
        EmailAccount.id == account_id,
        EmailAccount.user_id == current_user.id
    )
    
    result = db.execute(stmt)
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found"
        )
    
    return account


@router.post("/custom-domain", response_model=EmailAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_domain_account(
    account_data: EmailAccountCreateCustomDomain,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a custom domain email account.
    This will require DNS verification before emails can be sent.
    """
    # Check if email already exists for this user
    stmt = select(EmailAccount).where(
        EmailAccount.user_id == current_user.id,
        EmailAccount.email == account_data.email
    )
    result = db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email account already exists"
        )
    
    # If this is set as default, unset other defaults
    if account_data.is_default:
        stmt = select(EmailAccount).where(
            EmailAccount.user_id == current_user.id,
            EmailAccount.is_default == True
        )
        result = db.execute(stmt)
        for acc in result.scalars().all():
            acc.is_default = False
    
    # Create new account
    new_account = EmailAccount(
        user_id=current_user.id,
        account_type=EmailAccountType.CUSTOM_DOMAIN,
        email=account_data.email,
        name=account_data.name,
        domain=account_data.domain,
        is_default=account_data.is_default,
        is_verified=False,
        spf_verified=False,
        dkim_verified=False
    )
    
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    
    return new_account


@router.post("/gmail/auth-url")
async def get_gmail_auth_url(
    current_user: User = Depends(get_current_user)
):
    """
    Get Google OAuth authorization URL to connect Gmail account.
    """
    gmail_service = GmailOAuthService()
    
    # Use user ID as state for CSRF protection
    state = f"user_{current_user.id}"
    auth_url = gmail_service.get_authorization_url(state=state)
    
    return {
        "auth_url": auth_url,
        "instructions": (
            "Redirect the user to this URL to authorize Gmail access. "
            "They will be redirected back to the callback URL after authorization."
        )
    }


def _sending_settings_redirect(outcome: str) -> RedirectResponse:
    """Build a redirect back to the unified sending-config page with an outcome flag.

    Args:
        outcome: ``connected`` on success, otherwise an error slug.

    Returns:
        A 302 redirect to ``/dashboard/settings/sending?gmail=<outcome>``.
    """
    base = (getattr(settings, "frontend_url", "") or "http://localhost:3000").rstrip("/")
    return RedirectResponse(url=f"{base}/dashboard/settings/sending?gmail={outcome}")


@router.get("/gmail/callback")
async def gmail_oauth_callback(
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """
    Google OAuth redirect target: exchange the code and connect the Gmail account.

    This is the server-side completion of the Gmail connect flow. Google redirects
    the browser here (``GOOGLE_REDIRECT_URI``) with ``?code`` and the ``state`` we
    set at authorization time (``user_<id>``, which identifies the owner — no JWT
    is present on this cross-site redirect). On success or failure the browser is
    redirected back to the unified sending-config page with a ``?gmail=`` flag.
    """
    if error or not code:
        logger.warning("[Gmail OAuth] Callback without code (error=%r)", error)
        return _sending_settings_redirect("error")

    # state = "user_<id>" — the only link back to the authenticated owner.
    if not state.startswith("user_"):
        logger.warning("[Gmail OAuth] Callback with unexpected state=%r", state)
        return _sending_settings_redirect("error")
    try:
        user_id = int(state.removeprefix("user_"))
    except ValueError:
        return _sending_settings_redirect("error")

    gmail_service = GmailOAuthService()
    try:
        tokens = await gmail_service.exchange_code_for_tokens(code)
        user_info = await gmail_service.get_user_info(tokens["access_token"])
        gmail_email = user_info.get("email")
        if not user_info.get("verified_email") or not gmail_email:
            return _sending_settings_redirect("error")

        existing = db.execute(
            select(EmailAccount).where(
                EmailAccount.user_id == user_id,
                EmailAccount.email == gmail_email,
            )
        ).scalar_one_or_none()

        if existing is not None:
            # Re-authorising an already-connected account: refresh its tokens.
            existing.oauth_access_token = encryption_service.encrypt(tokens["access_token"])
            if tokens.get("refresh_token"):
                existing.oauth_refresh_token = encryption_service.encrypt(tokens["refresh_token"])
            existing.oauth_token_expires_at = tokens["expires_at"]
            existing.is_active = True
            existing.is_verified = True
            db.commit()
            return _sending_settings_redirect("connected")

        db.add(EmailAccount(
            user_id=user_id,
            account_type=EmailAccountType.GMAIL_OAUTH,
            email=gmail_email,
            name=user_info.get("name") or gmail_email,
            is_default=False,
            is_verified=True,  # Gmail accounts are auto-verified
            oauth_access_token=encryption_service.encrypt(tokens["access_token"]),
            oauth_refresh_token=encryption_service.encrypt(tokens.get("refresh_token", "")),
            oauth_token_expires_at=tokens["expires_at"],
        ))
        db.commit()
        return _sending_settings_redirect("connected")
    except Exception as exc:  # noqa: BLE001 — surface as a friendly redirect, never a 500
        logger.error("[Gmail OAuth] Callback failed for user %s: %s", user_id, exc)
        return _sending_settings_redirect("error")


@router.post("/{account_id}/verify-dns", response_model=DNSVerificationResponse)
async def verify_dns_records(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify DNS records (SPF/DKIM) for a custom domain email account.
    """
    # Get account
    stmt = select(EmailAccount).where(
        EmailAccount.id == account_id,
        EmailAccount.user_id == current_user.id
    )
    result = db.execute(stmt)
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found"
        )
    
    if account.account_type != EmailAccountType.CUSTOM_DOMAIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DNS verification is only for custom domain accounts"
        )
    
    # Verify DNS (real SPF/DKIM lookups)
    verification_result = await sending_domain_dns_service.verify_domain(account.domain)
    
    # Update account verification status
    account.spf_verified = verification_result["spf_verified"]
    account.dkim_verified = verification_result["dkim_verified"]
    account.is_verified = (
        verification_result["spf_verified"] and 
        verification_result["dkim_verified"]
    )
    
    db.commit()
    
    return DNSVerificationResponse(
        spf_verified=account.spf_verified,
        dkim_verified=account.dkim_verified,
        is_verified=account.is_verified,
        spf_record=verification_result.get("spf_record"),
        dkim_record=verification_result.get("dkim_instructions"),
        instructions=verification_result["instructions"]
    )


@router.patch("/{account_id}", response_model=EmailAccountResponse)
async def update_email_account(
    account_id: int,
    account_data: EmailAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an email account.
    """
    # Get account
    stmt = select(EmailAccount).where(
        EmailAccount.id == account_id,
        EmailAccount.user_id == current_user.id
    )
    result = db.execute(stmt)
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found"
        )
    
    # If setting as default, unset other defaults
    if account_data.is_default:
        stmt = select(EmailAccount).where(
            EmailAccount.user_id == current_user.id,
            EmailAccount.is_default == True,
            EmailAccount.id != account_id
        )
        result = db.execute(stmt)
        for acc in result.scalars().all():
            acc.is_default = False
    
    # Update fields
    if account_data.name is not None:
        account.name = account_data.name
    if account_data.is_default is not None:
        account.is_default = account_data.is_default
    if account_data.is_active is not None:
        account.is_active = account_data.is_active
    
    db.commit()
    db.refresh(account)
    
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an email account.
    """
    # Get account
    stmt = select(EmailAccount).where(
        EmailAccount.id == account_id,
        EmailAccount.user_id == current_user.id
    )
    result = db.execute(stmt)
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found"
        )
    
    db.delete(account)
    db.commit()
    
    return None

