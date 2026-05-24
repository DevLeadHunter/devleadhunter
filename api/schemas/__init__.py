"""
Pydantic schemas for request/response validation.
"""
from schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
    Token,
    TokenData
)
from schemas.credit_settings import (
    CreditSettingsResponse,
    CreditSettingsUpdate
)
from schemas.credit_transaction import (
    CreditTransactionResponse,
    CreditBalanceResponse,
    CreditTransactionCreate
)
from schemas.payment import (
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    PaymentStatusResponse
)
from schemas.accounting import (
    CreditPurchaseTransaction,
    AccountingSummary,
    AccountingResponse
)
from schemas.support import (
    SupportTicketCreate,
    SupportTicketUpdate,
    SupportTicketResponse,
    SupportTicketDetailResponse,
    SupportMessageCreate,
    SupportMessageResponse,
    SupportAttachmentResponse
)
from schemas.email_account import (
    EmailAccountCreateCustomDomain,
    EmailAccountCreateGmail,
    EmailAccountUpdate,
    EmailAccountResponse,
    DNSVerificationResponse,
    GmailAuthUrlResponse
)
from schemas.email_template import (
    EmailTemplateCreate,
    EmailTemplateUpdate,
    EmailTemplateResponse,
    EmailTemplatePreviewRequest,
    EmailTemplatePreviewResponse
)
from schemas.email_sending import (
    SendEmailRequest,
    SendCampaignEmailRequest,
    EmailLogResponse,
    EmailStatsResponse,
    SendEmailResponse
)
from schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignDetailResponse,
    CampaignListResponse,
    CampaignProspectAdd,
    CampaignProspectRemove,
    CampaignStats
)

__all__ = [
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "Token",
    "TokenData",
    "CreditSettingsResponse",
    "CreditSettingsUpdate",
    "CreditTransactionResponse",
    "CreditBalanceResponse",
    "CreditTransactionCreate",
    "CheckoutSessionCreate",
    "CheckoutSessionResponse",
    "PaymentStatusResponse",
    "CreditPurchaseTransaction",
    "AccountingSummary",
    "AccountingResponse",
    "SupportTicketCreate",
    "SupportTicketUpdate",
    "SupportTicketResponse",
    "SupportTicketDetailResponse",
    "SupportMessageCreate",
    "SupportMessageResponse",
    "SupportAttachmentResponse",
    "EmailAccountCreateCustomDomain",
    "EmailAccountCreateGmail",
    "EmailAccountUpdate",
    "EmailAccountResponse",
    "DNSVerificationResponse",
    "GmailAuthUrlResponse",
    "EmailTemplateCreate",
    "EmailTemplateUpdate",
    "EmailTemplateResponse",
    "EmailTemplatePreviewRequest",
    "EmailTemplatePreviewResponse",
    "SendEmailRequest",
    "SendCampaignEmailRequest",
    "EmailLogResponse",
    "EmailStatsResponse",
    "SendEmailResponse",
    "CampaignCreate",
    "CampaignUpdate",
    "CampaignResponse",
    "CampaignDetailResponse",
    "CampaignListResponse",
    "CampaignProspectAdd",
    "CampaignProspectRemove",
    "CampaignStats",
]
