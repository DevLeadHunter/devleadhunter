"""
Messages written on the contact page of the marketing site (devleadhunter.fr/contact).

Each message is mailed to the publisher's inbox from the platform admin's Resend identity, with the visitor as
Reply-To so a plain reply answers them, then raised as a notification for every platform admin.
"""

from __future__ import annotations

import html
import logging

from sqlalchemy.orm import Session

from core.config import settings
from enums.sending_provider import SendingProvider
from enums.user_role import is_platform_admin
from models.user import User
from schemas.site_contact import SiteContactRequest
from services.notification_service import notification_service
from services.resend_service import ResendService
from services.sending_identity import SendingIdentity, SendingNotConfiguredError, resolve_sending_identity

logger = logging.getLogger(__name__)

_SENDER_NAME = "DevLeadHunter"
_INTRO = "Nouveau message depuis la page contact de devleadhunter.fr. Répondez à cet e-mail pour répondre au visiteur."


class SiteContactDeliveryError(Exception):
    """The message could not be mailed: the visitor has to try again or call."""


class SiteContactService:
    """Mail a contact-page message to the publisher, then tell the admins about it."""

    def __init__(self, resend_service: ResendService | None = None) -> None:
        self._resend_service = resend_service or ResendService()

    async def send(self, db: Session, request: SiteContactRequest) -> None:
        """
        Mail the message to the publisher's inbox, then notify the admins.

        Args:
            db: Active database session.
            request: The visitor's message.

        Raises:
            SiteContactDeliveryError: When the message could not be mailed; the admins are told, with the
                visitor's address so they can still answer.
        """
        try:
            identity = self._resolve_sender_identity(db)
            await self._resend_service.send_email(
                from_email=identity.from_email,
                from_name=_SENDER_NAME,
                to_email=settings.contact_form_to,
                subject=f"Page contact · {request.topic.label} · {request.name}",
                html_body=self._build_html_body(request),
                text_body=self._build_text_body(request),
                api_key_override=identity.resend_api_key,
                reply_to=str(request.email),
            )
        except Exception as exc:
            logger.error("Contact page message from %s not mailed: %s", request.email, exc)
            await notification_service.notify_error(
                context="Page contact",
                message=f"Message de {request.email} non transmis : {exc}",
                tag="site-contact-failed",
            )
            raise SiteContactDeliveryError(str(exc)) from exc

        await notification_service.notify_site_contact(
            name=request.name,
            email=str(request.email),
            topic_label=request.topic.label,
            message=request.message,
        )

    @staticmethod
    def _resolve_sender_identity(db: Session) -> SendingIdentity:
        """
        Resolve the Resend identity that sends the publisher's own mail: the ``ADMIN_EMAIL`` account first.

        Args:
            db: Active database session.

        Returns:
            A Resend sending identity.

        Raises:
            SendingNotConfiguredError: When no active admin can send through Resend.
        """
        active_users = db.query(User).filter(User.is_active.is_(True)).all()
        admins = [user for user in active_users if user.email == settings.admin_email or is_platform_admin(user.role)]
        admins.sort(key=lambda admin: admin.email != settings.admin_email)
        for admin in admins:
            try:
                identity = resolve_sending_identity(db, admin.id)
            except SendingNotConfiguredError:
                continue
            if identity.provider == SendingProvider.RESEND.value:
                return identity
        raise SendingNotConfiguredError("Aucun administrateur ne peut envoyer d'e-mail par Resend")

    @staticmethod
    def _build_detail_rows(request: SiteContactRequest) -> list[tuple[str, str]]:
        """
        Build the label and value pairs that describe the message.

        Args:
            request: The visitor's message.

        Returns:
            The pairs, in reading order.
        """
        return [
            ("Sujet", request.topic.label),
            ("Nom", request.name),
            ("E-mail", str(request.email)),
            ("Téléphone", request.phone or "non renseigné"),
            ("Langue du site", (request.locale or "fr").upper()),
        ]

    @classmethod
    def _build_html_body(cls, request: SiteContactRequest) -> str:
        """
        Build the HTML email, every visitor value escaped.

        Args:
            request: The visitor's message.

        Returns:
            The HTML body.
        """
        rows = "".join(
            f"<tr><td style='padding:4px 16px 4px 0;color:#6b6355'>{html.escape(label)}</td>"
            f"<td style='padding:4px 0'>{html.escape(value)}</td></tr>"
            for label, value in cls._build_detail_rows(request)
        )
        return (
            "<div style='font-family:system-ui,-apple-system,sans-serif;font-size:15px;line-height:1.6;color:#1b1813'>"
            f"<p style='margin:0 0 12px'>{html.escape(_INTRO)}</p>"
            f"<table style='border-collapse:collapse;margin:0 0 16px'>{rows}</table>"
            "<div style='white-space:pre-wrap;border-top:1px solid #e3dccd;padding-top:12px'>"
            f"{html.escape(request.message)}</div>"
            "</div>"
        )

    @classmethod
    def _build_text_body(cls, request: SiteContactRequest) -> str:
        """
        Build the plain-text email.

        Args:
            request: The visitor's message.

        Returns:
            The text body.
        """
        details = "\n".join(f"{label} : {value}" for label, value in cls._build_detail_rows(request))
        return f"{_INTRO}\n\n{details}\n\n{request.message}"


site_contact_service = SiteContactService()
