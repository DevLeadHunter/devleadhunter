"""
The email the publisher receives for each message of the marketing site's contact page.

A white card on the site's paper, with the reply deadline, the visitor's name, one-tap actions (reply, call, WhatsApp),
the message and its details. Table-based HTML with inline styles, so Gmail, Outlook and Apple Mail render it alike.
"""

from __future__ import annotations

import html
import re
from calendar import FRIDAY
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import quote

from schemas.site_contact import SiteContactRequest
from services.french_date_formatter import FrenchDateFormatter
from services.sms.phone_normalizer import to_e164_fr, to_e164_mobile

_LOGO_URL = "https://devleadhunter.fr/apple-touch-icon.png"
_FONTS_URL = (
    "https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600"
    "&family=Spline+Sans+Mono:wght@500&display=swap"
)
_DISPLAY_FONT = "'Fraunces', Georgia, 'Times New Roman', serif"
_BODY_FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
_LABEL_FONT = "'Spline Sans Mono', ui-monospace, Menlo, Consolas, monospace"
_PAPER = "#f6f3ec"
_INK = "#1b1813"
_INK_SOFT = "#6b6355"
_LINE = "#e3dccd"
_LINK_UNDERLINE = "#cfc6b4"
_AMBER = "#e8a33c"
_BUTTON_TEXT = "#fcfaf5"
_PREHEADER_LENGTH = 120
_LOCALE_NAMES: dict[str, str] = {"fr": "Français", "en": "Anglais"}
_REPLY_SUBJECTS: dict[str, str] = {
    "fr": "Votre message sur devleadhunter.fr",
    "en": "Your message on devleadhunter.fr",
}


@dataclass(frozen=True)
class SiteContactEmailAction:
    """A button of the email: what it says and what it opens."""

    label: str
    href: str
    is_primary: bool = False


@dataclass(frozen=True)
class SiteContactEmailDetailRow:
    """A line of the details table, linked when the value can be tapped (email, phone)."""

    label: str
    value: str
    href: str | None = None


@dataclass(frozen=True)
class RenderedSiteContactEmail:
    """A ready-to-send subject, HTML body and plain-text body."""

    subject: str
    html: str
    text: str


class SiteContactEmail:
    """Renders the email of one contact-page message."""

    @classmethod
    def render(cls, request: SiteContactRequest, received_at: datetime) -> RenderedSiteContactEmail:
        """
        Render the email of a contact-page message.

        Args:
            request: The visitor's message.
            received_at: When the message arrived, in Paris time.

        Returns:
            The subject, the HTML body and its plain-text version; every visitor value is escaped in the HTML.
        """
        subject = f"Nouveau message · {request.name} · {request.topic.label}"
        deadline = FrenchDateFormatter.long_date(cls._next_business_day(received_at))
        actions = cls._build_actions(request)
        rows = cls._build_detail_rows(request, received_at)
        return RenderedSiteContactEmail(
            subject=subject,
            html=cls._build_html(request, subject, received_at, deadline, actions, rows),
            text=cls._build_text(request, deadline, rows),
        )

    @staticmethod
    def _next_business_day(moment: datetime) -> datetime:
        """
        Find the weekday after ``moment``: a message of Friday or of the weekend is due on Monday.

        Args:
            moment: When the message arrived.

        Returns:
            The same time on the next weekday.
        """
        days_ahead = 7 - moment.weekday() if moment.weekday() >= FRIDAY else 1
        return moment + timedelta(days=days_ahead)

    @staticmethod
    def _build_tel_href(phone: str) -> str:
        """
        Build the ``tel:`` link of a phone number typed by the visitor.

        Args:
            phone: The phone number as typed.

        Returns:
            The link, international when the number is recognized.
        """
        international = to_e164_mobile(phone) or to_e164_fr(phone)
        return f"tel:{international or re.sub(r'[^0-9+]', '', phone)}"

    @classmethod
    def _build_actions(cls, request: SiteContactRequest) -> list[SiteContactEmailAction]:
        """
        Build the buttons: reply first, then call and WhatsApp when the visitor left a number.

        Args:
            request: The visitor's message.

        Returns:
            The buttons, the reply one highlighted.
        """
        reply_subject = _REPLY_SUBJECTS.get(request.locale or "fr", _REPLY_SUBJECTS["fr"])
        reply_href = f"mailto:{request.email}?subject={quote(reply_subject)}"
        actions = [SiteContactEmailAction(label="Répondre", href=reply_href, is_primary=True)]
        if request.phone:
            actions.append(SiteContactEmailAction(label="Appeler", href=cls._build_tel_href(request.phone)))
            mobile = to_e164_mobile(request.phone)
            if mobile:
                actions.append(SiteContactEmailAction(label="WhatsApp", href=f"https://wa.me/{mobile[1:]}"))
        return actions

    @classmethod
    def _build_detail_rows(cls, request: SiteContactRequest, received_at: datetime) -> list[SiteContactEmailDetailRow]:
        """
        Build the details table: how to reach the visitor, the topic, the site language and the reception date.

        Args:
            request: The visitor's message.
            received_at: When the message arrived, in Paris time.

        Returns:
            The rows, without the phone when none was given.
        """
        rows = [SiteContactEmailDetailRow(label="E‑mail", value=str(request.email), href=f"mailto:{request.email}")]
        if request.phone:
            phone_href = cls._build_tel_href(request.phone)
            rows.append(SiteContactEmailDetailRow(label="Téléphone", value=request.phone, href=phone_href))
        locale = request.locale or "fr"
        received = f"{FrenchDateFormatter.long_date(received_at)} à {received_at:%H:%M}"
        rows.append(SiteContactEmailDetailRow(label="Sujet", value=request.topic.label))
        rows.append(SiteContactEmailDetailRow(label="Langue du site", value=_LOCALE_NAMES.get(locale, locale)))
        rows.append(SiteContactEmailDetailRow(label="Reçu le", value=received))
        return rows

    @classmethod
    def _build_html(
        cls,
        request: SiteContactRequest,
        subject: str,
        received_at: datetime,
        deadline: str,
        actions: list[SiteContactEmailAction],
        rows: list[SiteContactEmailDetailRow],
    ) -> str:
        """
        Build the HTML document: header, card and footer on the site's paper.

        Args:
            request: The visitor's message.
            subject: The email subject, also the document title.
            received_at: When the message arrived, in Paris time.
            deadline: The day the visitor should get an answer, in French words.
            actions: The buttons of the card.
            rows: The details table of the card.

        Returns:
            The full HTML document.
        """
        preheader = " ".join(request.message.split())[:_PREHEADER_LENGTH]
        name = html.escape(request.name)
        return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="x-apple-disable-message-reformatting">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<title>{html.escape(subject)}</title>
<link href="{html.escape(_FONTS_URL)}" rel="stylesheet">
<style>
@media only screen and (max-width: 480px) {{
  .card-cell {{ padding: 28px 20px !important; }}
  .card {{ border-radius: 0 !important; border-left: 0 !important; border-right: 0 !important; }}
  .edge {{ padding-left: 20px !important; padding-right: 20px !important; }}
  .title {{ font-size: 26px !important; line-height: 32px !important; }}
  .action-button {{ padding-left: 16px !important; padding-right: 16px !important; }}
  .detail-label {{ width: 104px !important; }}
}}
</style>
</head>
<body style="margin:0;padding:0;background-color:{_PAPER};">
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">{html.escape(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{_PAPER};">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;">
{cls._build_header(received_at)}
{cls._build_card(request, deadline, actions, rows)}
<tr><td class="edge" style="padding:24px 0 40px;font-family:{_BODY_FONT};font-size:12px;line-height:18px;color:{_INK_SOFT};">
Envoyé par le formulaire de contact de devleadhunter.fr. Répondre à cet e‑mail écrit directement à {name}.
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""

    @staticmethod
    def _build_header(received_at: datetime) -> str:
        """
        Build the header row: the DevLeadHunter mark, « Nouveau message » and the reception time.

        Args:
            received_at: When the message arrived, in Paris time.

        Returns:
            The header row of the layout table.
        """
        return f"""<tr><td class="edge" style="padding:32px 0 20px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr>
<td style="font-size:0;line-height:0;"><img src="{_LOGO_URL}" width="28" height="28" alt="DevLeadHunter" style="display:inline-block;vertical-align:middle;width:28px;height:28px;border:0;border-radius:7px;"><span style="display:inline-block;vertical-align:middle;margin-left:10px;font-family:{_DISPLAY_FONT};font-size:19px;line-height:28px;font-weight:600;color:{_INK};">Nouveau message</span></td>
<td align="right" style="font-family:{_BODY_FONT};font-size:13px;line-height:28px;color:{_INK_SOFT};white-space:nowrap;">{FrenchDateFormatter.short_date_time(received_at)}</td>
</tr>
</table>
</td></tr>"""

    @classmethod
    def _build_card(
        cls,
        request: SiteContactRequest,
        deadline: str,
        actions: list[SiteContactEmailAction],
        rows: list[SiteContactEmailDetailRow],
    ) -> str:
        """
        Build the white card: deadline, visitor's name, buttons, message and details.

        Args:
            request: The visitor's message.
            deadline: The day the visitor should get an answer, in French words.
            actions: The buttons.
            rows: The details table.

        Returns:
            The card row of the layout table.
        """
        buttons = "".join(cls._build_button(action) for action in actions)
        message = "<br>".join(html.escape(line) for line in request.message.splitlines())
        detail_rows = "".join(cls._build_detail_row(row) for row in rows)
        return f"""<tr><td class="card" style="background-color:#ffffff;border:1px solid {_LINE};border-radius:16px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><td class="card-cell" style="padding:40px;font-family:{_BODY_FONT};">
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
<tr><td style="padding:7px 12px;background-color:{_PAPER};border-radius:8px;font-size:13px;line-height:18px;color:{_INK};"><span style="display:inline-block;width:6px;height:6px;margin-right:8px;border-radius:3px;background-color:{_AMBER};vertical-align:middle;"></span>À répondre au plus tard <strong style="font-weight:600;white-space:nowrap;">{deadline}</strong></td></tr>
</table>
<div class="title" style="padding-top:22px;font-family:{_DISPLAY_FONT};font-size:30px;line-height:36px;font-weight:600;letter-spacing:-0.3px;color:{_INK};">{html.escape(request.name)}</div>
<div style="padding-top:6px;font-size:15px;line-height:22px;color:{_INK_SOFT};">{html.escape(request.topic.label)} · page contact de devleadhunter.fr</div>
<div style="padding-top:24px;font-size:0;line-height:0;">{buttons}</div>
<div style="padding-top:20px;font-family:{_LABEL_FONT};font-size:11px;line-height:16px;letter-spacing:1.8px;text-transform:uppercase;color:{_INK_SOFT};"><span style="display:inline-block;width:18px;height:2px;margin-right:8px;background-color:{_AMBER};vertical-align:middle;"></span>Message</div>
<div style="margin-top:10px;padding:18px 20px;background-color:{_PAPER};border-radius:12px;font-size:15px;line-height:24px;color:{_INK};word-break:break-word;">{message}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:28px;border-collapse:collapse;">
{detail_rows}
</table>
</td></tr>
</table>
</td></tr>"""

    @staticmethod
    def _build_button(action: SiteContactEmailAction) -> str:
        """
        Build one pill button: ink for the main action, outlined for the others.

        Args:
            action: The button to draw.

        Returns:
            The button link.
        """
        colors = (
            f"background-color:{_INK};border:1px solid {_INK};color:{_BUTTON_TEXT};font-weight:600;"
            if action.is_primary
            else f"background-color:#ffffff;border:1px solid {_LINE};color:{_INK};font-weight:500;"
        )
        return (
            f'<a class="action-button" href="{html.escape(action.href)}" style="display:inline-block;margin:0 8px 8px 0;padding:12px 22px;'
            f"{colors}border-radius:999px;font-family:{_BODY_FONT};font-size:15px;line-height:20px;"
            f'text-decoration:none;">{html.escape(action.label)}</a>'
        )

    @staticmethod
    def _build_detail_row(row: SiteContactEmailDetailRow) -> str:
        """
        Build one line of the details table, the value linked when it can be tapped.

        Args:
            row: The line to draw.

        Returns:
            The table row.
        """
        value = html.escape(row.value)
        if row.href:
            value = (
                f'<a href="{html.escape(row.href)}" style="color:{_INK};text-decoration:underline;'
                f'text-decoration-color:{_LINK_UNDERLINE};">{value}</a>'
            )
        return (
            f'<tr><td class="detail-label" width="130" valign="top" style="width:130px;padding:11px 12px 11px 0;'
            f'border-top:1px solid {_LINE};font-size:14px;line-height:20px;color:{_INK_SOFT};">{html.escape(row.label)}</td>'
            f'<td valign="top" style="padding:11px 0;border-top:1px solid {_LINE};font-size:14px;line-height:20px;'
            f'font-weight:500;color:{_INK};word-break:break-word;">{value}</td></tr>'
        )

    @staticmethod
    def _build_text(request: SiteContactRequest, deadline: str, rows: list[SiteContactEmailDetailRow]) -> str:
        """
        Build the plain-text version, for the mail clients that do not show HTML.

        Args:
            request: The visitor's message.
            deadline: The day the visitor should get an answer, in French words.
            rows: The details table.

        Returns:
            The text body.
        """
        lines = [
            f"Nouveau message de {request.name}",
            f"{request.topic.label} · page contact de devleadhunter.fr",
            f"À répondre au plus tard {deadline}",
            "",
            "Message :",
            request.message,
            "",
            *(f"{row.label} : {row.value}" for row in rows),
        ]
        return "\n".join(lines)
