"""
Pydantic schemas for request/response validation.
"""

from schemas.accounting import AccountingResponse, AccountingSummary, CreditPurchaseTransaction
from schemas.campaign import (
    CampaignCreate,
    CampaignDetailResponse,
    CampaignListResponse,
    CampaignProspectAdd,
    CampaignProspectRemove,
    CampaignResponse,
    CampaignStats,
    CampaignUpdate,
)
from schemas.credit_settings import CreditSettingsResponse, CreditSettingsUpdate
from schemas.credit_transaction import CreditBalanceResponse, CreditTransactionCreate, CreditTransactionResponse
from schemas.email_account import (
    DNSVerificationResponse,
    EmailAccountCreateCustomDomain,
    EmailAccountCreateGmail,
    EmailAccountResponse,
    EmailAccountUpdate,
    GmailAuthUrlResponse,
)
from schemas.email_sending import (
    EmailLogResponse,
    EmailStatsResponse,
    SendCampaignEmailRequest,
    SendEmailRequest,
    SendEmailResponse,
)
from schemas.email_template import (
    EmailTemplateCreate,
    EmailTemplatePreviewRequest,
    EmailTemplatePreviewResponse,
    EmailTemplateResponse,
    EmailTemplateUpdate,
)
from schemas.payment import CheckoutSessionCreate, CheckoutSessionResponse, PaymentStatusResponse
from schemas.support import (
    SupportAttachmentResponse,
    SupportMessageCreate,
    SupportMessageResponse,
    SupportTicketCreate,
    SupportTicketDetailResponse,
    SupportTicketResponse,
    SupportTicketUpdate,
)
from schemas.user import Token, TokenData, UserCreate, UserLogin, UserResponse, UserUpdate

__all__ = [
    "AccountingResponse",
    "AccountingSummary",
    "CampaignCreate",
    "CampaignDetailResponse",
    "CampaignListResponse",
    "CampaignProspectAdd",
    "CampaignProspectRemove",
    "CampaignResponse",
    "CampaignStats",
    "CampaignUpdate",
    "CheckoutSessionCreate",
    "CheckoutSessionResponse",
    "CreditBalanceResponse",
    "CreditPurchaseTransaction",
    "CreditSettingsResponse",
    "CreditSettingsUpdate",
    "CreditTransactionCreate",
    "CreditTransactionResponse",
    "DNSVerificationResponse",
    "EmailAccountCreateCustomDomain",
    "EmailAccountCreateGmail",
    "EmailAccountResponse",
    "EmailAccountUpdate",
    "EmailLogResponse",
    "EmailStatsResponse",
    "EmailTemplateCreate",
    "EmailTemplatePreviewRequest",
    "EmailTemplatePreviewResponse",
    "EmailTemplateResponse",
    "EmailTemplateUpdate",
    "GmailAuthUrlResponse",
    "PaymentStatusResponse",
    "SendCampaignEmailRequest",
    "SendEmailRequest",
    "SendEmailResponse",
    "SupportAttachmentResponse",
    "SupportMessageCreate",
    "SupportMessageResponse",
    "SupportTicketCreate",
    "SupportTicketDetailResponse",
    "SupportTicketResponse",
    "SupportTicketUpdate",
    "Token",
    "TokenData",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserUpdate",
]
