"""Parsing of smsmode incoming-message (MO) callbacks — the STOP opt-out path.

smsmode posts an incoming reply (Mobile-Originated) to the ``callbackUrlMo`` we set
on each send. A STOP opt-out is flagged with ``body.stop == true`` (its text is the
STOP keyword). The MO also carries ``originMessageId`` (the id of the sent SMS it
replies to) and ``refClient`` (our ``dlh-<id>``), so the prospect resolves precisely
— the recipient number is only a fallback. All helpers are pure and tolerate
nested / camelCase shapes, like the DLR helpers.

In France the prospect answers « STOP » to the short code smsmode appended, and the reply
reaches this callback. To a foreign number smsmode appends an unsubscribe link instead
(``no-sms.eu``): the opt-out is then held by smsmode in the account's exclusion list, and
only reaches us when a callback (MO or DLR) says so — our own suppression list is written
whenever it does, so both lists agree.
"""

from __future__ import annotations

from typing import Any

# Textual STOP keywords a prospect can reply to the short code smsmode appends.
_STOP_KEYWORDS: frozenset[str] = frozenset(
    {"STOP", "STOPSMS", "STOP SMS", "UNSUBSCRIBE", "DESABONNEMENT", "DÉSABONNEMENT", "DESABO"}
)


def mo_is_stop(payload: dict[str, Any]) -> bool:
    """Whether an incoming MO message is a STOP opt-out.

    Args:
        payload: The MO callback JSON body.

    Returns:
        ``True`` when smsmode flags it a STOP (``body.stop``) or the text is a STOP keyword.
    """
    body = payload.get("body")
    if isinstance(body, dict):
        if body.get("stop") is True:
            return True
        if str(body.get("text") or "").strip().upper() in _STOP_KEYWORDS:
            return True
    if payload.get("stop") is True:
        return True
    return str(payload.get("text") or payload.get("message") or "").strip().upper() in _STOP_KEYWORDS


def mo_sender_number(payload: dict[str, Any]) -> str:
    """The prospect's mobile number behind the MO, tolerating nested shapes.

    Args:
        payload: The MO callback JSON body.

    Returns:
        The raw number (``recipient.to`` first), or "" when none is present. A non-number
        (e.g. the alphanumeric sender id) is left for the caller's E.164 validation to reject.
    """
    recipient = payload.get("recipient")
    if isinstance(recipient, dict):
        value = str(recipient.get("to") or "").strip()
        if value:
            return value
    for key in ("to", "msisdn", "from", "recipient", "sender"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def mo_origin_message_id(payload: dict[str, Any]) -> str:
    """The provider id of the sent SMS this MO replies to (``originMessageId``)."""
    for key in ("originMessageId", "origin_message_id"):
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    return ""


def mo_ref_client(payload: dict[str, Any]) -> str:
    """Our echoed reference (``dlh-<id>``), a fallback to resolve the sent SMS."""
    for key in ("refClient", "ref_client", "reference"):
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    return ""
