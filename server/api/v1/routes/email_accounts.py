"""
Email accounts routes for managing user's email sender configurations.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from core.database import get_db
from models.user import User
from models.email_account import EmailAccount
from schemas.email_account import (
    EmailAccountCreateCustomDomain,
    EmailAccountCreateGmail,
    EmailAccountUpdate,
    EmailAccountResponse,
    DNSVerificationResponse
)
from services.auth_service import get_current_user
from services.mailjet_service import MailjetService
from services.gmail_oauth_service import GmailOAuthService
from services.encryption_service import encryption_service
from enums.email_account_type import EmailAccountType
import json

router = APIRouter(prefix="/email-accounts", tags=["email-accounts"])


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


@router.post("/gmail/connect", response_model=EmailAccountResponse, status_code=status.HTTP_201_CREATED)
async def connect_gmail_account(
    account_data: EmailAccountCreateGmail,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Connect a Gmail account using OAuth authorization code.
    """
    gmail_service = GmailOAuthService()
    
    try:
        # Exchange code for tokens
        tokens = await gmail_service.exchange_code_for_tokens(account_data.oauth_code)
        
        # Get user info to verify email
        user_info = await gmail_service.get_user_info(tokens["access_token"])
        
        if not user_info.get("verified_email"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gmail account is not verified"
            )
        
        gmail_email = user_info.get("email")
        
        # Check if this Gmail account is already connected
        stmt = select(EmailAccount).where(
            EmailAccount.user_id == current_user.id,
            EmailAccount.email == gmail_email
        )
        result = db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This Gmail account is already connected"
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
        
        # Create new Gmail account with encrypted tokens
        new_account = EmailAccount(
            user_id=current_user.id,
            account_type=EmailAccountType.GMAIL_OAUTH,
            email=gmail_email,
            name=account_data.name or user_info.get("name", gmail_email),
            is_default=account_data.is_default,
            is_verified=True,  # Gmail accounts are auto-verified
            oauth_access_token=encryption_service.encrypt(tokens["access_token"]),
            oauth_refresh_token=encryption_service.encrypt(tokens.get("refresh_token", "")),
            oauth_token_expires_at=tokens["expires_at"]
        )
        
        db.add(new_account)
        db.commit()
        db.refresh(new_account)
        
        return new_account
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect Gmail account: {str(e)}"
        )


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
    
    # Verify DNS
    mailjet_service = MailjetService()
    verification_result = await mailjet_service.verify_dns_records(account.domain)
    
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

