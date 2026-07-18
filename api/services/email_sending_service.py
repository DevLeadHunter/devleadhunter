"""
Email sending service - orchestrates sending via Resend or Gmail.
"""
import logging
from typing import Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from models.email_account import EmailAccount
from models.email_template import EmailTemplate
from models.email_log import EmailLog
from services.demo_identity import posthog_distinct_id, resolve_demo_slug
from services.gmail_oauth_service import GmailOAuthService
from services.posthog_service import posthog_service
from services.resend_service import ResendService
from services.unsubscribe_service import unsubscribe_service
from services.encryption_service import encryption_service
from services.sending_identity import SendingIdentity, resolve_sending_identity
from enums.email_account_type import EmailAccountType
from enums.sending_provider import SendingProvider
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
        self.gmail_service = GmailOAuthService()
        self.resend_service = ResendService()

    def _apply_dev_redirect(self, recipient_email: str, subject: str) -> tuple[str, str]:
        """
        Reroute every outbound email to a single test inbox in development.

        When ``DEV_EMAIL_REDIRECT`` is set, no email ever reaches a real prospect:
        the recipient is swapped for the dev address and the original recipient is
        kept visible in the subject. A no-op (returns inputs unchanged) in prod.
        """
        redirect = getattr(settings, "dev_email_redirect", None)
        if redirect:
            logger.warning("[DEV] Email rerouted %s -> %s", recipient_email, redirect)
            return redirect, f"[DEV→{recipient_email}] {subject}"
        return recipient_email, subject

    def _mark_prospect_contacted(self, prospect_id: Optional[str]) -> None:
        """
        Flag a prospect as contacted after a successful send (idempotent).

        Never raises: a bookkeeping failure must not turn a successful send into a
        failure.
        """
        if not prospect_id:
            return
        try:
            from models.prospect_db import ProspectDB

            prospect = (
                self.db.query(ProspectDB).filter(ProspectDB.id == int(prospect_id)).first()
            )
            if prospect and not prospect.contacted:
                prospect.contacted = True
                self.db.commit()
        except Exception as exc:  # noqa: BLE001 — never block a send on bookkeeping
            logger.warning("Could not mark prospect %s as contacted: %s", prospect_id, exc)

    async def _capture_email_sent(
        self,
        *,
        user_id: int,
        prospect_id: Optional[str],
        campaign_id: Optional[str],
        email_log_id: int,
        recipient_email: str,
        ab_variant: Optional[str] = None,
    ) -> None:
        """
        Mirror a successful send into PostHog as an ``email_sent`` event.

        This is the FIRST step of the ``email → démo → vente`` funnel. The send
        path sets ``status = SENT`` synchronously, so Resend's ``email.sent``
        webhook arrives at an equal rank and won't emit it — we emit it here, at
        the source. ``distinct_id`` = the prospect's demo slug so it resolves to
        the same PostHog person as the demo capture. Best-effort: never raises,
        never blocks a send.

        @param user_id - Owner of the send (scopes the demo-slug lookup).
        @param prospect_id - Prospect id (string from the send API), for slug + props.
        @param campaign_id - Campaign id (string), stamped on the event.
        @param email_log_id - EmailLog row id, stamped on the event.
        @param recipient_email - Recipient address, last-resort identity.
        @param ab_variant - A/B variant ('A'/'B') when known, stamped on the event.
        """
        try:
            pid: Optional[int] = int(prospect_id) if prospect_id else None
            demo_slug: Optional[str] = resolve_demo_slug(self.db, user_id, pid)
            await posthog_service.capture(
                distinct_id=posthog_distinct_id(demo_slug, pid, recipient_email),
                event="email_sent",
                properties={
                    "demo_slug": demo_slug,
                    "prospect_id": pid,
                    "campaign_id": int(campaign_id) if campaign_id else None,
                    "ab_variant": ab_variant,
                    "email_log_id": email_log_id,
                    "$lib": "devleadhunter-api",
                },
            )
        except Exception as exc:  # noqa: BLE001 — tracking must never break a send
            logger.warning("PostHog email_sent capture failed (log=%s): %s", email_log_id, exc)

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

        # Dev safety: reroute every outbound email to a single test inbox (no-op in prod).
        recipient_email, subject = self._apply_dev_redirect(recipient_email, subject)

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
            # Send via appropriate provider. Custom-domain accounts also send via Resend
            # (the domain is verified in Resend and used as the from address).
            if email_account.account_type in (
                EmailAccountType.RESEND,
                EmailAccountType.CUSTOM_DOMAIN,
            ):
                result = await self._send_via_resend(
                    email_account=email_account,
                    recipient_email=recipient_email,
                    recipient_name=recipient_name,
                    subject=subject,
                    body_html=body_html,
                    body_text=body_text,
                    custom_id=str(email_log.id),
                    unsubscribe_link=unsubscribe_link,
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
            self._mark_prospect_contacted(prospect_id)
            await self._capture_email_sent(
                user_id=user_id,
                prospect_id=prospect_id,
                campaign_id=campaign_id,
                email_log_id=email_log.id,
                recipient_email=recipient_email,
            )

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
    
    @staticmethod
    def _unsubscribe_headers(unsubscribe_link: str) -> Dict[str, str]:
        """RFC 8058 one-click unsubscribe headers (Gmail/Yahoo bulk-sender requirement).

        Args:
            unsubscribe_link: The per-recipient unsubscribe URL (GET and POST both work).

        Returns:
            The ``List-Unsubscribe`` / ``List-Unsubscribe-Post`` header pair.
        """
        return {
            "List-Unsubscribe": f"<{unsubscribe_link}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
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
        unsubscribe_link: Optional[str] = None,
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
            extra_headers=self._unsubscribe_headers(unsubscribe_link) if unsubscribe_link else None,
        )

    async def _send_via_gmail(
        self,
        email_account: EmailAccount,
        recipient_email: str,
        subject: str,
        body_html: str,
        recipient_name: Optional[str] = None,
        body_text: Optional[str] = None,
        unsubscribe_link: Optional[str] = None,
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
            text_body=body_text,
            extra_headers=self._unsubscribe_headers(unsubscribe_link) if unsubscribe_link else None,
        )
    
    async def send_via_user_identity(
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
        Send an email via the user's active sending identity (Resend or Gmail).

        This is the unified send path for campaigns, follow-ups, orders and
        one-off sends. The provider is resolved once, from ``users.sending_provider``
        (see :func:`services.sending_identity.resolve_sending_identity`), and all
        the cross-cutting concerns — dev redirect, RGPD unsubscribe check + footer,
        one-click unsubscribe headers, ``EmailLog`` bookkeeping and the PostHog
        ``email_sent`` capture — are applied here regardless of provider. No
        ``EmailAccount`` selection is required from the caller.

        Args:
            user_id:         Owner of the sending identity.
            recipient_email: Recipient address.
            subject:         Email subject (already variable-substituted).
            body_html:       Email HTML body (already variable-substituted).
            recipient_name:  Recipient display name (optional).
            prospect_id:     Prospect ID for logging / unsubscribe link (optional).
            campaign_id:     Campaign ID for logging (optional).
            ab_variant:      A/B variant ('A'/'B') stamped on the log (optional).

        Returns:
            Dict with ``success``, ``email_log_id`` and ``message_id`` / ``error``.

        Raises:
            SendingNotConfiguredError: When the active provider is not configured.
        """
        # Resolve the provider once (raises SendingNotConfiguredError if unusable).
        identity: SendingIdentity = resolve_sending_identity(self.db, user_id)

        # Dev safety: reroute every outbound email to a single test inbox (no-op in prod).
        recipient_email, subject = self._apply_dev_redirect(recipient_email, subject)

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
            # Gmail sends are tied to their EmailAccount (per-account health stats);
            # Resend sends have no account row.
            email_account_id=identity.gmail_account.id if identity.gmail_account else None,
            prospect_id=prospect_id,
            campaign_id=campaign_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body_html=body_html,
            status=EmailStatus.PENDING.value,
            provider=identity.provider,
            ab_variant=ab_variant,
        )
        self.db.add(email_log)
        self.db.commit()
        self.db.refresh(email_log)

        try:
            if identity.provider == SendingProvider.GMAIL.value:
                result = await self._send_via_gmail(
                    email_account=identity.gmail_account,
                    recipient_email=recipient_email,
                    recipient_name=recipient_name,
                    subject=subject,
                    body_html=body_html,
                    unsubscribe_link=unsubscribe_link,
                )
            else:
                result = await self.resend_service.send_email(
                    from_email=identity.from_email,
                    from_name=identity.from_name,
                    to_email=recipient_email,
                    to_name=recipient_name,
                    subject=subject,
                    html_body=body_html,
                    custom_id=str(email_log.id),
                    api_key_override=identity.resend_api_key,
                    # RFC 8058 one-click unsubscribe — required by Gmail/Yahoo for bulk
                    # senders; the POST route exists on /api/v1/unsubscribe.
                    extra_headers=self._unsubscribe_headers(unsubscribe_link),
                )
            email_log.status = EmailStatus.SENT.value
            email_log.provider = result.get("provider", identity.provider)
            email_log.provider_message_id = result.get("message_id")
            email_log.sent_at = datetime.utcnow()
            self.db.commit()
            self._mark_prospect_contacted(prospect_id)
            await self._capture_email_sent(
                user_id=user_id,
                prospect_id=prospect_id,
                campaign_id=campaign_id,
                email_log_id=email_log.id,
                recipient_email=recipient_email,
                ab_variant=ab_variant,
            )
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
            logger.error(f"Failed to send via user identity ({identity.provider}): {e}")
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

