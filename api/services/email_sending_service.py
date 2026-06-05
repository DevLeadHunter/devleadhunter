"""
Email sending service - orchestrates sending via Mailjet or Gmail.
"""
import logging
from typing import Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from models.email_account import EmailAccount
from models.email_template import EmailTemplate
from models.email_log import EmailLog
from services.mailjet_service import MailjetService
from services.gmail_oauth_service import GmailOAuthService
from services.resend_service import ResendService
from services.unsubscribe_service import unsubscribe_service
from services.encryption_service import encryption_service
from enums.email_account_type import EmailAccountType
from enums.email_status import EmailStatus
from core.config import settings
import json

logger = logging.getLogger(__name__)


class EmailSendingService:
    """
    Service for orchestrating email sending via different providers.
    """
    
    def __init__(self, db: Session):
        """Initialize email sending service."""
        self.db = db
        self.mailjet_service = MailjetService()
        self.gmail_service = GmailOAuthService()
        self.resend_service = ResendService()
    
    async def send_email(
        self,
        user_id: int,
        email_account_id: int,
        recipient_email: str,
        subject: str,
        body_html: str,
        recipient_name: Optional[str] = None,
        body_text: Optional[str] = None,
        prospect_id: Optional[str] = None,
        campaign_id: Optional[str] = None
    ) -> Dict:
        """
        Send a single email.
        
        Args:
            user_id: User ID
            email_account_id: Email account to send from
            recipient_email: Recipient email address
            subject: Email subject
            body_html: Email HTML body
            recipient_name: Recipient name (optional)
            body_text: Email plain text body (optional)
            prospect_id: Prospect ID (optional)
            campaign_id: Campaign ID (optional)
        
        Returns:
            Dict with success status and email log ID
        """
        # Get email account
        stmt = select(EmailAccount).where(
            EmailAccount.id == email_account_id,
            EmailAccount.user_id == user_id
        )
        result = self.db.execute(stmt)
        email_account = result.scalar_one_or_none()
        
        if not email_account:
            raise Exception("Email account not found")
        
        if not email_account.is_active:
            raise Exception("Email account is not active")
        
        if not email_account.is_verified:
            raise Exception("Email account is not verified. Please verify DNS records or reconnect Gmail.")
        
        # Check if email is unsubscribed (RGPD)
        if unsubscribe_service.is_unsubscribed(self.db, recipient_email):
            raise Exception(f"Email {recipient_email} has unsubscribed from our emails")
        
        # Add unsubscribe link to email body (RGPD compliance)
        base_url = getattr(settings, 'frontend_url', 'http://localhost:8000')
        unsubscribe_link = unsubscribe_service.generate_unsubscribe_link(
            recipient_email,
            int(prospect_id) if prospect_id else None,
            base_url
        )
        body_html = unsubscribe_service.add_unsubscribe_footer(body_html, unsubscribe_link)
        
        # Create email log
        email_log = EmailLog(
            user_id=user_id,
            email_account_id=email_account_id,
            prospect_id=prospect_id,
            campaign_id=campaign_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body_html=body_html,
            status=EmailStatus.PENDING,
            provider=""
        )
        
        self.db.add(email_log)
        self.db.commit()
        self.db.refresh(email_log)
        
        try:
            # Send via appropriate provider
            if email_account.account_type == EmailAccountType.RESEND:
                result = await self._send_via_resend(
                    email_account=email_account,
                    recipient_email=recipient_email,
                    recipient_name=recipient_name,
                    subject=subject,
                    body_html=body_html,
                    body_text=body_text,
                    custom_id=str(email_log.id)
                )
            elif email_account.account_type == EmailAccountType.CUSTOM_DOMAIN:
                result = await self._send_via_mailjet(
                    email_account=email_account,
                    recipient_email=recipient_email,
                    recipient_name=recipient_name,
                    subject=subject,
                    body_html=body_html,
                    body_text=body_text,
                    custom_id=str(email_log.id)
                )
            elif email_account.account_type == EmailAccountType.GMAIL_OAUTH:
                result = await self._send_via_gmail(
                    email_account=email_account,
                    recipient_email=recipient_email,
                    recipient_name=recipient_name,
                    subject=subject,
                    body_html=body_html,
                    body_text=body_text
                )
            else:
                raise Exception(f"Unsupported account type: {email_account.account_type}")
            
            # Update email log
            email_log.status = EmailStatus.SENT
            email_log.provider = result["provider"]
            email_log.provider_message_id = result.get("message_id")
            email_log.sent_at = datetime.utcnow()
            
            self.db.commit()
            
            return {
                "success": True,
                "email_log_id": email_log.id,
                "message_id": result.get("message_id")
            }
            
        except Exception as e:
            # Update email log with error
            email_log.status = EmailStatus.FAILED
            email_log.error_message = str(e)
            email_log.failed_at = datetime.utcnow()
            self.db.commit()
            
            logger.error(f"Failed to send email: {str(e)}")
            
            return {
                "success": False,
                "email_log_id": email_log.id,
                "error": str(e)
            }
    
    async def _send_via_resend(
        self,
        email_account: EmailAccount,
        recipient_email: str,
        subject: str,
        body_html: str,
        recipient_name: Optional[str] = None,
        body_text: Optional[str] = None,
        custom_id: Optional[str] = None,
    ) -> Dict:
        """Send email via Resend."""
        return await self.resend_service.send_email(
            from_email=email_account.email,
            from_name=email_account.name,
            to_email=recipient_email,
            to_name=recipient_name,
            subject=subject,
            html_body=body_html,
            text_body=body_text,
            custom_id=custom_id,
        )

    async def _send_via_mailjet(
        self,
        email_account: EmailAccount,
        recipient_email: str,
        subject: str,
        body_html: str,
        recipient_name: Optional[str] = None,
        body_text: Optional[str] = None,
        custom_id: Optional[str] = None
    ) -> Dict:
        """Send email via Mailjet."""
        return await self.mailjet_service.send_email(
            from_email=email_account.email,
            from_name=email_account.name,
            to_email=recipient_email,
            to_name=recipient_name,
            subject=subject,
            html_body=body_html,
            text_body=body_text,
            custom_id=custom_id
        )
    
    async def _send_via_gmail(
        self,
        email_account: EmailAccount,
        recipient_email: str,
        subject: str,
        body_html: str,
        recipient_name: Optional[str] = None,
        body_text: Optional[str] = None
    ) -> Dict:
        """Send email via Gmail OAuth."""
        # Decrypt access token
        try:
            access_token = encryption_service.decrypt(email_account.oauth_access_token)
        except Exception as e:
            raise Exception(f"Failed to decrypt access token: {str(e)}")
        
        # Check if token needs refresh
        if email_account.oauth_token_expires_at and \
           email_account.oauth_token_expires_at < datetime.utcnow():
            # Refresh token
            try:
                refresh_token = encryption_service.decrypt(email_account.oauth_refresh_token)
                tokens = await self.gmail_service.refresh_access_token(refresh_token)
                email_account.oauth_access_token = encryption_service.encrypt(tokens["access_token"])
                email_account.oauth_token_expires_at = tokens["expires_at"]
                self.db.commit()
                access_token = tokens["access_token"]
            except Exception as e:
                raise Exception(f"Failed to refresh Gmail token: {str(e)}")
        
        return await self.gmail_service.send_email(
            access_token=access_token,
            from_email=email_account.email,
            to_email=recipient_email,
            to_name=recipient_name,
            subject=subject,
            html_body=body_html,
            text_body=body_text
        )
    
    async def send_via_resend_config(
        self,
        user_id: int,
        recipient_email: str,
        subject: str,
        body_html: str,
        recipient_name: Optional[str] = None,
        prospect_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        ab_variant: Optional[str] = None,
    ) -> Dict:
        """
        Send an email using the user's ResendConfig — no EmailAccount needed.

        This is the unified send path for campaigns and one-off sends: one user
        has exactly one Resend sending identity (from_email / API key), stored
        in the ``resend_config`` table.  No account selection is required.

        Args:
            user_id:         Owner of the ResendConfig.
            recipient_email: Recipient address.
            subject:         Email subject (already variable-substituted).
            body_html:       Email HTML body (already variable-substituted).
            recipient_name:  Recipient display name (optional).
            prospect_id:     Prospect ID for logging / unsubscribe link (optional).
            campaign_id:     Campaign ID for logging (optional).
            ab_variant:      A/B variant ('A'/'B') stamped on the log (optional).

        Returns:
            Dict with ``success``, ``email_log_id`` and ``message_id`` / ``error``.
        """
        from models.resend_config import ResendConfig

        config = self.db.execute(
            select(ResendConfig).where(ResendConfig.user_id == user_id)
        ).scalar_one_or_none()

        if config is None or not config.api_key:
            raise Exception("Resend non configuré — Paramètres → Configuration Resend")

        api_key = encryption_service.decrypt(config.api_key)
        from_email = config.from_email
        from_name = config.from_name or ""

        # RGPD: never send to an unsubscribed address.
        if unsubscribe_service.is_unsubscribed(self.db, recipient_email):
            raise Exception(f"{recipient_email} s'est désabonné")

        base_url = getattr(settings, "frontend_url", "http://localhost:3000")
        unsubscribe_link = unsubscribe_service.generate_unsubscribe_link(
            recipient_email,
            int(prospect_id) if prospect_id else None,
            base_url,
        )
        body_html = unsubscribe_service.add_unsubscribe_footer(body_html, unsubscribe_link)

        email_log = EmailLog(
            user_id=user_id,
            email_account_id=None,
            prospect_id=prospect_id,
            campaign_id=campaign_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body_html=body_html,
            status=EmailStatus.PENDING.value,
            provider="resend",
            ab_variant=ab_variant,
        )
        self.db.add(email_log)
        self.db.commit()
        self.db.refresh(email_log)

        try:
            result = await self.resend_service.send_email(
                from_email=from_email,
                from_name=from_name,
                to_email=recipient_email,
                to_name=recipient_name,
                subject=subject,
                html_body=body_html,
                custom_id=str(email_log.id),
                api_key_override=api_key,
            )
            email_log.status = EmailStatus.SENT.value
            email_log.provider_message_id = result.get("message_id")
            email_log.sent_at = datetime.utcnow()
            self.db.commit()
            return {
                "success": True,
                "email_log_id": email_log.id,
                "message_id": result.get("message_id"),
            }
        except Exception as e:  # noqa: BLE001
            email_log.status = EmailStatus.FAILED.value
            email_log.error_message = str(e)
            email_log.failed_at = datetime.utcnow()
            self.db.commit()
            logger.error(f"Failed to send via resend_config: {e}")
            return {"success": False, "email_log_id": email_log.id, "error": str(e)}

    def replace_variables(self, text: str, variables: dict) -> str:
        """Replace variables in text with values."""
        for key, value in variables.items():
            text = text.replace(f"{{{key}}}", str(value))
        return text
    
    async def send_campaign_emails(
        self,
        user_id: int,
        email_account_id: int,
        campaign_id: str,
        template_id: int,
        prospect_ids: list,
        variables_per_prospect: Optional[Dict[str, Dict[str, str]]] = None
    ) -> Dict:
        """
        Send emails to multiple prospects using a template.
        
        Args:
            user_id: User ID
            email_account_id: Email account to send from
            campaign_id: Campaign ID
            template_id: Email template ID
            prospect_ids: List of prospect IDs
            variables_per_prospect: Map of prospect_id to variable values
        
        Returns:
            Dict with campaign sending results
        """
        # Get template
        stmt = select(EmailTemplate).where(
            EmailTemplate.id == template_id,
            EmailTemplate.user_id == user_id
        )
        result = self.db.execute(stmt)
        template = result.scalar_one_or_none()
        
        if not template:
            raise Exception("Email template not found")
        
        # Parse template variables
        template_variables = json.loads(template.variables) if template.variables else []
        
        sent_count = 0
        failed_count = 0
        email_log_ids = []
        errors = []
        
        # Note: In a real production environment, you'd want to:
        # 1. Use a task queue (Celery, Redis Queue, etc.) for async processing
        # 2. Add rate limiting to respect provider limits
        # 3. Add retry logic with exponential backoff
        # 4. Batch sends for better performance
        
        for prospect_id in prospect_ids:
            try:
                # Get variables for this prospect
                variables = variables_per_prospect.get(prospect_id, {}) if variables_per_prospect else {}
                
                # Replace variables in subject and body
                subject = self.replace_variables(template.subject, variables)
                body_html = self.replace_variables(template.body_html, variables)
                body_text = None
                
                # Get recipient email from variables (should be passed)
                recipient_email = variables.get("email")
                recipient_name = variables.get("name")
                
                if not recipient_email:
                    errors.append(f"No email for prospect {prospect_id}")
                    failed_count += 1
                    continue
                
                # Send email
                result = await self.send_email(
                    user_id=user_id,
                    email_account_id=email_account_id,
                    recipient_email=recipient_email,
                    subject=subject,
                    body_html=body_html,
                    recipient_name=recipient_name,
                    body_text=body_text,
                    prospect_id=prospect_id,
                    campaign_id=campaign_id
                )
                
                email_log_ids.append(result["email_log_id"])
                
                if result["success"]:
                    sent_count += 1
                else:
                    failed_count += 1
                    errors.append(f"Prospect {prospect_id}: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                failed_count += 1
                errors.append(f"Prospect {prospect_id}: {str(e)}")
                logger.error(f"Failed to send email to prospect {prospect_id}: {str(e)}")
        
        return {
            "success": sent_count > 0,
            "total_emails": len(prospect_ids),
            "sent_count": sent_count,
            "failed_count": failed_count,
            "email_log_ids": email_log_ids,
            "errors": errors if errors else None
        }

