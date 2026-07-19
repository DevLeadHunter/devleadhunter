"""
Email sending service - orchestrates sending via Resend or Gmail.
"""
import logging
from typing import Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session

from models.email_account import EmailAccount
from models.email_log import EmailLog
from services.demo_identity import posthog_distinct_id, resolve_demo_slug
from services.gmail_oauth_service import GmailOAuthService
from services.posthog_service import posthog_service
from services.resend_service import ResendService
from services.unsubscribe_service import unsubscribe_service
from services.encryption_service import encryption_service
from services.sending_identity import SendingIdentity, resolve_sending_identity
from enums.sending_provider import SendingProvider
from enums.email_status import EmailStatus
from core.config import settings

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

