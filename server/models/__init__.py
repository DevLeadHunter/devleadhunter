"""
Models package for Prospect Tool API.
"""
from models.user import User
from models.health import HealthStatus
from models.prospect import Prospect
from models.search import ProspectSearchRequest, ProspectSearchResponse
from models.credit_settings import CreditSettings
from models.credit_transaction import CreditTransaction
from models.support_ticket import SupportTicket
from models.support_message import SupportMessage
from models.support_attachment import SupportAttachment
from models.email_account import EmailAccount
from models.email_template import EmailTemplate
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from models.scraping_job import ScrapingJob
from models.campaign import Campaign, CampaignStatus
from models.email_unsubscribe import EmailUnsubscribe
from models.prospect_interaction import ProspectInteraction

__all__ = [
    "User",
    "HealthStatus",
    "Prospect",
    "ProspectSearchRequest",
    "ProspectSearchResponse",
    "CreditSettings",
    "CreditTransaction",
    "SupportTicket",
    "SupportMessage",
    "SupportAttachment",
    "EmailAccount",
    "EmailTemplate",
    "EmailLog",
    "ProspectDB",
    "ScrapingJob",
    "Campaign",
    "CampaignStatus",
    "EmailUnsubscribe",
    "ProspectInteraction",
]
