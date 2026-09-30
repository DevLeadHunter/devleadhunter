"""
Conversation service — the email thread between the user and a prospect.

Builds the chronological exchange (outbound sends + captured replies), tracks
which replies still await an answer (« à traiter »), and sends threaded answers
from the app (RFC ``In-Reply-To`` / ``References`` headers so the prospect's mail
client keeps the discussion in one thread).

Reply bodies are exposed as PLAIN TEXT only: inbound HTML is untrusted content —
it is stripped server-side rather than sanitized-and-rendered.
"""

from __future__ import annotations

import html as html_lib
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.email_log import EmailLog
from models.email_reply import EmailReply
from models.prospect_db import ProspectDB
from services import reply_intent_service
from services.email_sending_service import EmailSendingService
from services.email_signatures import render_default_signature_html
from services.reply_inbox_forward_service import inbox_copy_address
from services.sending_identity import resolve_sending_identity

_TAG_RE: re.Pattern[str] = re.compile(r"<[^>]+>")
_BLOCK_BREAK_RE: re.Pattern[str] = re.compile(r"(?i)<\s*(?:br|/p|/div|/tr|/li|/h[1-6])[^>]*>")
_SCRIPT_STYLE_RE: re.Pattern[str] = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>")

# Markers that begin the quoted original in a reply — everything from the first
# one on is the history we sent (with tracking URLs), not the prospect's words.
_QUOTE_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?im)^\s*Le\s.+?a\s+écrit\s*:\s*$"),  # « Le 31 août 2026 à 16:01, X a écrit : »
    re.compile(r"(?im)^\s*On\s.+?\bwrote\s*:\s*$"),  # « On Mon, …, X wrote: »
    re.compile(r"(?im)^\s*-{2,}\s*(?:Original Message|Message d['’]origine)\s*-{2,}\s*$"),
    re.compile(r"(?m)^_{5,}\s*$"),  # Outlook separator line
    re.compile(r"(?m)^\s*>"),  # first quoted line
)


def strip_quoted_reply(text: str) -> str:
    """Keep only the prospect's own words, dropping the quoted original + tracking URLs.

    Args:
        text: The full reply body (the prospect's text followed by our quoted email).

    Returns:
        The text up to the first quote marker, or the whole text when none is found.
    """
    cut = len(text)
    for marker in _QUOTE_MARKERS:
        match = marker.search(text)
        if match:
            cut = min(cut, match.start())
    trimmed = text[:cut].rstrip()
    return trimmed or text.strip()


def html_to_text(raw_html: str) -> str:
    """
    Flatten untrusted HTML to display-safe plain text.

    Args:
        raw_html: Inbound HTML body.

    Returns:
        Plain text with block tags folded to newlines and entities unescaped.
    """
    without_hidden = _SCRIPT_STYLE_RE.sub("", raw_html)
    with_breaks = _BLOCK_BREAK_RE.sub("\n", without_hidden)
    text = _TAG_RE.sub("", with_breaks)
    text = html_lib.unescape(text)
    # Collapse the blank-line noise HTML mail generates.
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def reply_display_text(reply: EmailReply) -> str:
    """The reply's own words as safe plain text (quoted history + tracking URLs removed)."""
    if reply.body_text and reply.body_text.strip():
        return strip_quoted_reply(reply.body_text)
    if reply.body_html:
        return strip_quoted_reply(html_to_text(reply.body_html))
    return ""


def build_reply_subject(original: str | None) -> str:
    """``Re: <subject>`` without stacking prefixes (Re:, RE:, Fwd:…)."""
    base = (original or "").strip()
    while True:
        stripped = re.sub(r"(?i)^(re|fwd|tr)\s*:\s*", "", base)
        if stripped == base:
            break
        base = stripped
    return f"Re: {base}" if base else "Re:"


def thread_headers_for(reply: EmailReply) -> dict[str, str] | None:
    """RFC threading headers pointing at the prospect's message, or None without a Message-ID."""
    if not reply.message_id:
        return None
    return {"In-Reply-To": reply.message_id, "References": reply.message_id}


class ConversationService:
    """Thread listing, pending queue and threaded answers."""

    # ------------------------------------------------------------------ #
    # Thread listing
    # ------------------------------------------------------------------ #

    @staticmethod
    def _thread_queries(log: EmailLog) -> tuple[Any, Any]:
        """The (sends, replies) queries scoping *log*'s thread: prospect first, address fallback."""
        logs_query = select(EmailLog).where(EmailLog.user_id == log.user_id)
        replies_query = (
            select(EmailReply)
            .join(EmailLog, EmailReply.email_log_id == EmailLog.id)
            .where(EmailReply.user_id == log.user_id)
        )
        if log.prospect_id is not None:
            logs_query = logs_query.where(EmailLog.prospect_id == log.prospect_id)
            replies_query = replies_query.where(EmailLog.prospect_id == log.prospect_id)
        else:
            logs_query = logs_query.where(EmailLog.recipient_email == log.recipient_email)
            replies_query = replies_query.where(EmailLog.recipient_email == log.recipient_email)
        return logs_query, replies_query

    async def backfill_intents(self, db: Session, user_id: int, email_log_id: int, *, limit: int = 5) -> None:
        """
        Classify the thread's unclassified replies (replies captured before the
        intent feature, or whose call failed at capture). Bounded, best-effort,
        and each verdict is persisted — so this converges to zero LLM calls.

        Args:
            db: Active database session.
            user_id: Owner of the thread.
            email_log_id: Any send belonging to the thread.
            limit: Maximum replies to classify in one pass.
        """
        log: EmailLog | None = db.get(EmailLog, email_log_id)
        if log is None or log.user_id != user_id:
            return
        _, replies_query = self._thread_queries(log)
        rows = (
            db.execute(
                replies_query.where(EmailReply.intent.is_(None), EmailReply.is_auto_reply.is_(False)).limit(limit)
            )
            .scalars()
            .all()
        )
        for reply in rows:
            try:
                await reply_intent_service.classify_reply(db, reply, reply_display_text(reply))
            except Exception:  # pragma: no cover — never break the conversation view
                return

    def get_conversation(self, db: Session, user_id: int, email_log_id: int) -> list[dict[str, Any]] | None:
        """
        Return the full exchange around a send, oldest first.

        The thread is scoped to the prospect when the log has one, otherwise to
        the recipient address — so manual sends without a prospect still thread.

        Args:
            db: Active database session.
            user_id: Owner of the emails.
            email_log_id: Any send belonging to the thread.

        Returns:
            Ordered items (``direction``: outbound | inbound), or ``None`` when
            the log does not exist or belongs to another user.
        """
        log: EmailLog | None = db.get(EmailLog, email_log_id)
        if log is None or log.user_id != user_id:
            return None

        logs_query, replies_query = self._thread_queries(log)

        items: list[dict[str, Any]] = []
        for row in db.execute(logs_query).scalars():
            when = row.sent_at or row.created_at
            items.append(
                {
                    "direction": "outbound",
                    "id": row.id,
                    "subject": row.subject,
                    "body_text": None,
                    "body_html": row.body_html,
                    "counterpart": row.recipient_email,
                    "timestamp": when.isoformat() if when else None,
                    "is_auto_reply": False,
                    "is_conversation_reply": bool(row.is_conversation_reply),
                    "pending": False,
                    "status": row.status,
                    "intent": None,
                    "reply_id": None,
                }
            )
        for reply in db.execute(replies_query).scalars():
            when = reply.received_at or reply.created_at
            items.append(
                {
                    "direction": "inbound",
                    "id": reply.id,
                    "subject": reply.subject,
                    "body_text": reply_display_text(reply),
                    "body_html": None,  # inbound HTML is untrusted — never shipped to the UI
                    "counterpart": reply.from_email,
                    "timestamp": when.isoformat() if when else None,
                    "is_auto_reply": bool(reply.is_auto_reply),
                    "is_conversation_reply": False,
                    "pending": reply.handled_at is None and not reply.is_auto_reply,
                    "status": None,
                    "intent": reply.intent,
                    "reply_id": reply.id,
                }
            )
        items.sort(key=lambda item: str(item["timestamp"] or ""))
        return items

    # ------------------------------------------------------------------ #
    # « À traiter » queue
    # ------------------------------------------------------------------ #

    def pending_replies(self, db: Session, user_id: int) -> list[dict[str, Any]]:
        """
        Human replies still awaiting an answer, newest first.

        Args:
            db: Active database session.
            user_id: Owner of the replies.

        Returns:
            One item per pending reply, with prospect name when known.
        """
        rows = (
            db.execute(
                select(EmailReply)
                .where(
                    EmailReply.user_id == user_id,
                    EmailReply.handled_at.is_(None),
                    EmailReply.is_auto_reply.is_(False),
                )
                .order_by(EmailReply.id.desc())
            )
            .scalars()
            .all()
        )
        prospect_ids = [reply.prospect_id for reply in rows if reply.prospect_id]
        prospects: dict[int, str] = {}
        if prospect_ids:
            for prospect in db.execute(select(ProspectDB).where(ProspectDB.id.in_(prospect_ids))).scalars():
                prospects[prospect.id] = prospect.name or ""
        return [
            {
                "source": "email_reply",
                "id": reply.id,
                "email_log_id": reply.email_log_id,
                "demo_lead_id": None,
                "prospect_id": reply.prospect_id,
                "prospect_name": prospects.get(reply.prospect_id or -1) or None,
                "from_email": reply.from_email,
                "subject": reply.subject,
                "preview": reply_display_text(reply)[:180],
                "intent": reply.intent,
                "received_at": (reply.received_at or reply.created_at).isoformat()
                if (reply.received_at or reply.created_at)
                else None,
            }
            for reply in rows
        ]

    def mark_handled(self, db: Session, user_id: int, reply_id: int) -> bool:
        """
        Mark one reply as dealt with (e.g. answered from the user's own mailbox).

        Args:
            db: Active database session.
            user_id: Owner of the reply.
            reply_id: The reply to mark.

        Returns:
            ``True`` when the reply existed and belongs to the user.
        """
        reply: EmailReply | None = db.get(EmailReply, reply_id)
        if reply is None or reply.user_id != user_id:
            return False
        if reply.handled_at is None:
            reply.handled_at = datetime.now(UTC).replace(tzinfo=None)
            db.commit()
        return True

    # ------------------------------------------------------------------ #
    # Threaded answer from the app
    # ------------------------------------------------------------------ #

    async def send_reply(self, db: Session, user_id: int, reply_id: int, body_html: str) -> dict[str, Any]:
        """
        Answer a prospect's reply from the app, threaded into their mail client.

        Sends to the address that actually wrote (not the original recipient),
        with ``Re:`` subject and RFC threading headers, then marks every pending
        reply from that sender as handled.

        Args:
            db: Active database session.
            user_id: Owner of the conversation.
            reply_id: The reply being answered.
            body_html: The answer's HTML body.

        Returns:
            The send result (``success`` / ``email_log_id`` / ``error``), or
            ``{"success": False, "error": "not_found"}`` for a foreign reply.
        """
        reply: EmailReply | None = db.get(EmailReply, reply_id)
        if reply is None or reply.user_id != user_id:
            return {"success": False, "error": "not_found"}

        original: EmailLog | None = db.get(EmailLog, reply.email_log_id)
        subject = build_reply_subject(reply.subject or (original.subject if original else None))

        signature_html = render_default_signature_html(db, user_id)
        full_body_html = f"{body_html}{signature_html}" if signature_html else body_html

        identity = resolve_sending_identity(db, user_id)
        copy_to = inbox_copy_address(identity)
        bcc: list[str] | None = [copy_to] if copy_to else None

        sending = EmailSendingService(db)
        result = await sending.send_via_user_identity(
            user_id=user_id,
            recipient_email=reply.from_email,
            subject=subject,
            body_html=full_body_html,
            prospect_id=str(reply.prospect_id) if reply.prospect_id else None,
            is_conversation_reply=True,
            thread_headers=thread_headers_for(reply),
            bcc=bcc,
        )

        if result.get("success"):
            from services.demo_lead_inbox_service import demo_lead_inbox_service

            now = datetime.now(UTC).replace(tzinfo=None)
            pending = db.execute(
                select(EmailReply).where(
                    EmailReply.user_id == user_id,
                    EmailReply.from_email == reply.from_email,
                    EmailReply.handled_at.is_(None),
                )
            ).scalars()
            for row in pending:
                row.handled_at = now
            db.commit()
            if reply.prospect_id:
                demo_lead_inbox_service.mark_handled_for_prospect(db, user_id, reply.prospect_id)
        return result


conversation_service = ConversationService()
