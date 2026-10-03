"""
Unsubscribe service for managing email unsubscriptions (RGPD compliance).
"""

import hashlib
import hmac
from html import escape
from urllib.parse import quote

from sqlalchemy.orm import Session

from core.config import settings
from models.email_unsubscribe import EmailUnsubscribe
from models.user import User
from services.country_profiles import CountryProfiles

POSTAL_ADDRESS_MISSING_REFUSAL: str = (
    "Adresse postale manquante dans votre profil : obligatoire pour écrire au Québec (loi CASL)"
)


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

    # Opening tag of the generated footer — the anchor both the builder and the stripper rely on.
    _FOOTER_MARKER: str = (
        '<div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; '
        'font-size: 12px; color: #999; text-align: center;">'
    )

    @staticmethod
    def _postal_address_on_one_line(sender: User | None) -> str:
        """The sender's profile address on one footer line: the line breaks typed in the profile become commas."""
        if sender is None:
            return ""
        lines = [line.strip().strip(",").strip() for line in (sender.postal_address or "").splitlines()]
        return ", ".join(line for line in lines if line)

    def sender_identification_line(self, country: str | None, sender: User | None) -> str:
        """
        The sender identification a country's anti-spam law puts in the footer, empty elsewhere.

        Canada (CASL) wants the sender named with a postal address in every commercial email. Both come
        from the profile of the user who sends: « Envoyé par Dibodev (Jean Dupont), 12 rue … », or
        « Envoyé par Jean Dupont, 12 rue … » when the profile has no company name. Without an address
        there is no line.

        Args:
            country: ISO code of the recipient's country (``None`` reads as France).
            sender: The user who sends, ``None`` when unknown.

        Returns:
            The plain-text line, or an empty string.
        """
        if not CountryProfiles.get(country).email_footer_needs_postal_address:
            return ""
        postal_address = self._postal_address_on_one_line(sender)
        if sender is None or not postal_address:
            return ""
        name = (sender.name or "").strip()
        company_name = (sender.company_name or "").strip()
        is_company_named_after_sender: bool = company_name.casefold() == name.casefold()
        if company_name and name and not is_company_named_after_sender:
            sender_label = f"{company_name} ({name})"
        else:
            sender_label = company_name or name
        return f"Envoyé par {sender_label}, {postal_address}" if sender_label else f"Envoyé par {postal_address}"

    def sender_identification_refusal(self, country: str | None, sender: User | None) -> str | None:
        """
        Why a commercial email to *country* cannot leave yet: its law wants a sender postal address the profile lacks.

        Args:
            country: ISO code of the recipient's country (``None`` reads as France).
            sender: The user who sends, ``None`` when unknown.

        Returns:
            The French reason, or ``None`` when the email may leave.
        """
        if not CountryProfiles.get(country).email_footer_needs_postal_address:
            return None
        if self._postal_address_on_one_line(sender):
            return None
        return POSTAL_ADDRESS_MISSING_REFUSAL

    def add_unsubscribe_footer(
        self,
        html_body: str,
        unsubscribe_link: str,
        *,
        country: str | None = None,
        sender: User | None = None,
    ) -> str:
        """
        Add unsubscribe footer to email HTML body.

        Args:
            html_body: Original HTML body
            unsubscribe_link: Unsubscribe link URL
            country: ISO code of the recipient's country — Canada adds the sender's postal identification
            sender: The user who sends, whose profile gives that identification

        Returns:
            HTML body with unsubscribe footer
        """
        identification = self.sender_identification_line(country, sender)
        identification_html = f"    <p>\n        {escape(identification)}\n    </p>\n" if identification else ""
        footer = f"""
{self._FOOTER_MARKER}
    <p>
        Vous recevez cet email car vous êtes dans notre liste de prospects.
    </p>
{identification_html}    <p>
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

    def strip_unsubscribe_footer(self, html_body: str) -> str:
        """
        Remove a previously added unsubscribe footer so the body can be re-sent cleanly.

        A resend to a corrected address needs a fresh per-recipient footer; reusing the stored body
        (footer + the old recipient's link) would both duplicate the block and leak the wrong link.

        Args:
            html_body: A body that may already carry the generated footer.

        Returns:
            The body without the footer (``</body>`` and anything after it preserved), unchanged when
            no footer is present.
        """
        marker_index: int = html_body.find(self._FOOTER_MARKER)
        if marker_index == -1:
            return html_body
        after_marker: str = html_body[marker_index:]
        body_close_index: int = after_marker.find("</body>")
        suffix: str = after_marker[body_close_index:] if body_close_index != -1 else ""
        # Drop the single newline the footer inserted ahead of its marker, restoring the original body.
        prefix: str = html_body[:marker_index]
        if prefix.endswith("\n"):
            prefix = prefix[:-1]
        return prefix + suffix


# Singleton instance
unsubscribe_service = UnsubscribeService()
