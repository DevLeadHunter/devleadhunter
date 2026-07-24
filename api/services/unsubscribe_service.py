"""
Unsubscribe service for managing email unsubscriptions (RGPD compliance).
"""

import hashlib
import hmac
from urllib.parse import quote

from sqlalchemy.orm import Session

from core.config import settings
from models.email_unsubscribe import EmailUnsubscribe


def _normalize_email(email: str) -> str:
    """Canonical form used both for signing and for storage (lowercased, trimmed)."""
    return email.strip().lower()


class UnsubscribeService:
    """Service for managing email unsubscriptions."""

    def generate_token(self, email: str) -> str:
        """Compute the per-email unsubscribe token (HMAC-SHA256, keyed by SECRET_KEY).

        The token binds the link to a specific address so a stranger cannot forge an
        unsubscribe URL for an arbitrary prospect (unsubscribe-bombing). It is stable
        (no expiry) so a link stays valid for the lifetime of a sent email.

        Args:
            email: Email address the link is for.

        Returns:
            Hex HMAC digest to append to the unsubscribe link as ``&token=``.
        """
        message: bytes = _normalize_email(email).encode()
        return hmac.new(settings.secret_key.encode(), message, hashlib.sha256).hexdigest()

    def verify_token(self, email: str, token: str | None) -> bool:
        """Constant-time check that ``token`` matches ``email``.

        Args:
            email: Email address claimed by the request.
            token: Token supplied in the URL (may be missing on legacy links).

        Returns:
            True when the token is present and valid, False otherwise.
        """
        if not token:
            return False
        return hmac.compare_digest(token, self.generate_token(email))

    def is_unsubscribed(self, db: Session, email: str) -> bool:
        """
        Check if an email address is unsubscribed.

        Args:
            db: Database session
            email: Email address to check

        Returns:
            True if unsubscribed, False otherwise
        """
        unsubscribe = db.query(EmailUnsubscribe).filter(EmailUnsubscribe.email == email.lower()).first()

        return unsubscribe is not None

    def unsubscribe(
        self,
        db: Session,
        email: str,
        prospect_id: int | None = None,
        user_id: int | None = None,
        reason: str | None = None,
    ) -> EmailUnsubscribe:
        """
        Unsubscribe an email address.

        Args:
            db: Database session
            email: Email address to unsubscribe
            prospect_id: Optional prospect ID
            user_id: Optional user ID
            reason: Optional reason for unsubscribing

        Returns:
            Created or existing unsubscribe record
        """
        # Check if already unsubscribed
        existing = db.query(EmailUnsubscribe).filter(EmailUnsubscribe.email == email.lower()).first()

        if existing:
            return existing

        # Create new unsubscribe record
        unsubscribe = EmailUnsubscribe(email=email.lower(), prospect_id=prospect_id, user_id=user_id, reason=reason)

        db.add(unsubscribe)
        db.commit()
        db.refresh(unsubscribe)

        return unsubscribe

    def resubscribe(self, db: Session, email: str) -> bool:
        """
        Resubscribe an email address (remove from unsubscribe list).

        Args:
            db: Database session
            email: Email address to resubscribe

        Returns:
            True if resubscribed, False if not found
        """
        unsubscribe = db.query(EmailUnsubscribe).filter(EmailUnsubscribe.email == email.lower()).first()

        if not unsubscribe:
            return False

        db.delete(unsubscribe)
        db.commit()

        return True

    def generate_unsubscribe_link(
        self, email: str, prospect_id: int | None = None, base_url: str = "http://localhost:8000"
    ) -> str:
        """
        Generate an unsubscribe link for an email.

        Args:
            email: Email address
            prospect_id: Optional prospect ID
            base_url: Base URL of the application

        Returns:
            Unsubscribe link URL, signed with a per-email token so it cannot be
            forged for another address.
        """
        email_encoded = quote(email)
        token = self.generate_token(email)
        link = f"{base_url}/api/v1/unsubscribe?email={email_encoded}&token={token}"

        if prospect_id:
            link += f"&prospect_id={prospect_id}"

        return link

    def add_unsubscribe_footer(self, html_body: str, unsubscribe_link: str) -> str:
        """
        Add unsubscribe footer to email HTML body.

        Args:
            html_body: Original HTML body
            unsubscribe_link: Unsubscribe link URL

        Returns:
            HTML body with unsubscribe footer
        """
        footer = f"""
<div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #999; text-align: center;">
    <p>
        Vous recevez cet email car vous êtes dans notre liste de prospects.
    </p>
    <p>
        <a href="{unsubscribe_link}" style="color: #999; text-decoration: underline;">
            Se désabonner
        </a>
    </p>
</div>
"""

        # Try to insert before closing </body> tag
        if "</body>" in html_body:
            html_body = html_body.replace("</body>", f"{footer}</body>")
        else:
            # If no </body> tag, append to end
            html_body += footer

        return html_body


# Singleton instance
unsubscribe_service = UnsubscribeService()
