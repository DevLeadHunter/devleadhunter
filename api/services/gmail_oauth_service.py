"""
Gmail OAuth service for sending emails via Gmail API.
"""

import base64
import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, ClassVar

import httpx

from core.config import settings
from services.email_attachment import EmailAttachment
from services.google_oauth_client import google_oauth_client

logger = logging.getLogger(__name__)


class GmailOAuthService:
    """
    Service for sending emails via Gmail API using OAuth2.

    Its consent, tokens and profile go through the shared Google OAuth client (GOOGLE_CLIENT_ID and
    GOOGLE_CLIENT_SECRET), with its own scope and redirect address.
    """

    SCOPES: ClassVar[tuple[str, ...]] = ("https://www.googleapis.com/auth/gmail.send",)
    TIMEOUT_SECONDS: ClassVar[float] = 30.0

    def __init__(self):
        """Initialize Gmail OAuth service."""
        self.gmail_api_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

    def get_authorization_url(self, state: str | None = None) -> str:
        """
        Get Google OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        return google_oauth_client.authorization_url(
            scopes=self.SCOPES, redirect_uri=settings.google_redirect_uri, state=state
        )

    async def exchange_code_for_tokens(self, code: str) -> dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from Google

        Returns:
            Dict with access_token, refresh_token and expires_at (naive UTC)

        Raises:
            GoogleOAuthError: If token exchange fails
        """
        tokens = await google_oauth_client.exchange_code(
            code, redirect_uri=settings.google_redirect_uri, timeout_seconds=self.TIMEOUT_SECONDS
        )
        return {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expires_at": tokens.expires_at,
        }

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh an expired access token.

        Args:
            refresh_token: Refresh token

        Returns:
            Dict with the new access_token and its expires_at (naive UTC)

        Raises:
            GoogleOAuthError: If token refresh fails
        """
        tokens = await google_oauth_client.refresh(refresh_token, timeout_seconds=self.TIMEOUT_SECONDS)
        return {"access_token": tokens.access_token, "expires_at": tokens.expires_at}

    async def send_email(
        self,
        access_token: str,
        from_email: str,
        to_email: str,
        to_name: str | None,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        extra_headers: dict[str, str] | None = None,
        bcc: list[str] | None = None,
        attachments: list[EmailAttachment] | None = None,
    ) -> dict:
        """
        Send an email via Gmail API.

        Args:
            access_token: Valid OAuth access token
            from_email: Sender email (must match the authenticated Gmail account)
            to_email: Recipient email address
            to_name: Recipient name (optional)
            subject: Email subject
            html_body: HTML body
            text_body: Plain text body (optional)
            extra_headers: Additional MIME headers (e.g. RFC 8058
                ``List-Unsubscribe`` / ``List-Unsubscribe-Post``).

        Returns:
            Dict with message_id and status

        Raises:
            Exception: If email sending fails
        """
        try:
            # Body: text+html alternative when a text part is given, else html only.
            if text_body:
                body: MIMEText | MIMEMultipart = MIMEMultipart("alternative")
                body.attach(MIMEText(text_body, "plain"))
                body.attach(MIMEText(html_body, "html"))
            else:
                body = MIMEText(html_body, "html")

            # Wrap the body in a "mixed" envelope only when files are attached.
            if attachments:
                message: MIMEText | MIMEMultipart = MIMEMultipart("mixed")
                message.attach(body)
                for attachment in attachments:
                    part = MIMEApplication(attachment.content, _subtype=attachment.content_type.split("/")[-1])
                    part.add_header("Content-Disposition", "attachment", filename=attachment.filename)
                    message.attach(part)
            else:
                message = body

            message["From"] = from_email
            message["To"] = f"{to_name} <{to_email}>" if to_name else to_email
            message["Subject"] = subject
            if bcc:
                message["Bcc"] = ", ".join(bcc)

            # Custom headers (e.g. one-click unsubscribe) — parity with Resend.
            for header_name, header_value in (extra_headers or {}).items():
                message[header_name] = header_value

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            # Send via Gmail API
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

            payload = {"raw": raw_message}

            async with httpx.AsyncClient() as client:
                response = await client.post(self.gmail_api_url, headers=headers, json=payload, timeout=30.0)

                response.raise_for_status()
                result = response.json()

                return {
                    "success": True,
                    "message_id": result.get("id"),
                    "thread_id": result.get("threadId"),
                    "provider": "gmail",
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"Gmail API error: {e.response.text}")
            raise Exception(f"Failed to send email via Gmail: {e.response.text}")
        except Exception as e:
            logger.error(f"Error sending email via Gmail: {e!s}")
            raise

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """
        Get user information from Google.

        Args:
            access_token: Valid OAuth access token

        Returns:
            Dict with user email and name

        Raises:
            GoogleOAuthError: If Google refuses the token
        """
        profile = await google_oauth_client.user_info(access_token, timeout_seconds=self.TIMEOUT_SECONDS)
        return {
            "email": profile.get("email"),
            "name": profile.get("name"),
            "verified_email": profile.get("verified_email", False),
        }
