"""
Webhook endpoint for Resend email events.

Configure in your Resend dashboard:
  URL: https://your-api.com/api/v1/webhooks/resend
  Events: email.sent, email.delivered, email.opened, email.clicked,
          email.bounced, email.complained

Resend signs each request with a ``svix-signature`` header.
Set RESEND_WEBHOOK_SECRET in your .env to enable signature verification.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from enums.email_status import EmailStatus
from models.demo_site import DemoSite
from models.email_log import EmailLog
from services.posthog_service import posthog_service
from services.storyblok_service import storyblok_service
from services.templates.site_content import from_storyblok_site_content

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Complete map of all Resend email webhook event types → EmailStatus.
# Sources: https://resend.com/docs/dashboard/webhooks/event-types
_EVENT_STATUS_MAP: dict[str, str] = {
    "email.scheduled":        EmailStatus.SCHEDULED.value,
    "email.sent":             EmailStatus.SENT.value,
    "email.delivered":        EmailStatus.DELIVERED.value,
    "email.delivery_delayed": EmailStatus.DELIVERY_DELAYED.value,
    "email.opened":           EmailStatus.OPENED.value,
    "email.clicked":          EmailStatus.CLICKED.value,
    "email.bounced":          EmailStatus.BOUNCED.value,
    "email.complained":       EmailStatus.COMPLAINED.value,
    "email.failed":           EmailStatus.FAILED.value,
    "email.suppressed":       EmailStatus.SUPPRESSED.value,
    # email.received is for Resend inbound inbox — not relevant here.
}

# Maps each event type to the EmailLog timestamp column it populates.
_EVENT_TIMESTAMP_MAP: dict[str, str] = {
    "email.sent":             "sent_at",
    "email.delivered":        "delivered_at",
    "email.delivery_delayed": "delivered_at",
    "email.opened":           "opened_at",
    "email.clicked":          "clicked_at",
    "email.bounced":          "bounced_at",
    "email.complained":       "complained_at",
    "email.failed":           "failed_at",
    "email.suppressed":       "suppressed_at",
    # email.scheduled has no dedicated timestamp column.
}

# Numeric rank used to prevent status from moving backwards on late/duplicate
# webhook deliveries.  Equal-rank statuses do NOT overwrite each other
# (strict ``>`` comparison).
_STATUS_RANK: dict[str, int] = {
    EmailStatus.PENDING.value:          0,
    EmailStatus.SENDING.value:          1,
    EmailStatus.SCHEDULED.value:        1,
    EmailStatus.SENT.value:             2,
    EmailStatus.DELIVERY_DELAYED.value: 3,
    EmailStatus.DELIVERED.value:        4,
    EmailStatus.OPENED.value:           5,
    EmailStatus.CLICKED.value:          6,
    EmailStatus.BOUNCED.value:          7,
    EmailStatus.COMPLAINED.value:       7,
    EmailStatus.FAILED.value:           7,
    EmailStatus.SUPPRESSED.value:       7,
}

# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


def _verify_signature(
    body: bytes,
    svix_id: str,
    svix_timestamp: str,
    svix_signature: str,
) -> bool:
    """
    Verify the Svix webhook signature used by Resend.

    The signed content is ``{svix_id}.{svix_timestamp}.{body}``.
    The secret may be prefixed with ``whsec_`` which is stripped before
    base64-decoding.

    Returns ``True`` when the signature is valid.  Also returns ``True`` when
    no secret is configured so that local development works without a webhook
    secret (never do this in production).

    Args:
        body:           Raw request body bytes (already buffered).
        svix_id:        Value of the ``svix-id`` request header.
        svix_timestamp: Value of the ``svix-timestamp`` request header.
        svix_signature: Value of the ``svix-signature`` request header.

    Returns:
        ``True`` if the signature is valid or no secret is configured.
    """
    secret: str = getattr(settings, "resend_webhook_secret", "")
    if not secret:
        return True  # Dev mode — no secret configured

    signed_content: bytes = f"{svix_id}.{svix_timestamp}.".encode() + body

    raw_secret: str = secret.removeprefix("whsec_")
    try:
        key: bytes = base64.b64decode(raw_secret)
    except Exception:  # noqa: BLE001
        key = raw_secret.encode()

    expected_digest: bytes = hmac.new(key, signed_content, hashlib.sha256).digest()
    expected_b64: str = base64.b64encode(expected_digest).decode()

    # Svix may send several space-separated signatures; accept any valid one.
    for sig in svix_signature.split(" "):
        clean = sig.split(",", 1)[-1]  # strip "v1," version prefix
        if hmac.compare_digest(clean, expected_b64):
            return True
    return False


def _resolve_demo_slug(db: Session, email_log: EmailLog) -> str | None:
    """Return the prospect's most recent non-deleted demo slug (PostHog identity)."""
    if not email_log.prospect_id:
        return None
    site = db.execute(
        select(DemoSite)
        .where(
            DemoSite.prospect_id == email_log.prospect_id,
            DemoSite.user_id == email_log.user_id,
            DemoSite.status != DemoSiteStatus.DELETED.value,
        )
        .order_by(DemoSite.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    return site.slug if site else None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/resend", status_code=status.HTTP_204_NO_CONTENT)
async def resend_webhook(
    request: Request,
    svix_id: str = Header(default="", alias="svix-id"),
    svix_timestamp: str = Header(default="", alias="svix-timestamp"),
    svix_signature: str = Header(default="", alias="svix-signature"),
    db: Session = Depends(get_db),
) -> None:
    """
    Receive and process Resend webhook events.

    Looks up the corresponding ``EmailLog`` row by the ``email_log_id`` tag
    (set at send time) or by ``provider_message_id`` as a fallback, then
    advances the row's status and records the event timestamp.

    Duplicate events are ignored: a status can only move forward in rank.
    """
    body: bytes = await request.body()

    if not _verify_signature(body, svix_id, svix_timestamp, svix_signature):
        logger.warning("[Webhook] Invalid Resend signature — request rejected")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # Parse body directly from the already-buffered bytes to avoid a second
    # async read and to log the exact error on malformed JSON.
    try:
        payload: dict[str, Any] = json.loads(body)
    except json.JSONDecodeError as exc:
        logger.warning("[Webhook] Malformed JSON body: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        ) from exc

    event_type: str = payload.get("type", "")
    data: dict[str, Any] = payload.get("data", {})

    logger.info("[Webhook] Resend event=%s message_id=%s", event_type, data.get("email_id"))

    if event_type not in _EVENT_STATUS_MAP:
        # Unknown / unsubscribed event — acknowledge without error so Resend
        # does not retry delivery.
        return

    resend_message_id: str = data.get("email_id", "")

    # --- Locate the matching EmailLog row -----------------------------------

    email_log: EmailLog | None = None

    # Primary lookup: the ``email_log_id`` tag we attach at send time.
    tags: list[dict[str, str]] = data.get("tags", [])
    for tag in tags:
        if tag.get("name") == "email_log_id":
            raw_id = tag.get("value")
            if raw_id:
                try:
                    email_log = db.execute(
                        select(EmailLog).where(EmailLog.id == int(raw_id))
                    ).scalar_one_or_none()
                except (ValueError, TypeError):
                    logger.warning("[Webhook] Non-integer email_log_id tag value: %r", raw_id)
            break

    # Fallback: match by the provider-assigned message ID.
    if email_log is None and resend_message_id:
        email_log = db.execute(
            select(EmailLog).where(EmailLog.provider_message_id == resend_message_id)
        ).scalar_one_or_none()

    if email_log is None:
        logger.warning(
            "[Webhook] No EmailLog found for event=%s message_id=%s",
            event_type,
            resend_message_id,
        )
        return  # Acknowledge — nothing to update

    # --- Advance status (never downgrade) -----------------------------------

    new_status: str = _EVENT_STATUS_MAP[event_type]
    ts_col: str | None = _EVENT_TIMESTAMP_MAP.get(event_type)
    now: datetime = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC to match DB columns

    current_rank: int = _STATUS_RANK.get(email_log.status, 0)
    new_rank: int = _STATUS_RANK.get(new_status, 0)

    # Strict ``>`` so duplicate events at the same rank (e.g. two ``opened``
    # webhooks) do not overwrite the original timestamp.
    if new_rank > current_rank:
        email_log.status = new_status
        if ts_col:
            setattr(email_log, ts_col, now)
        if resend_message_id and not email_log.provider_message_id:
            email_log.provider_message_id = resend_message_id
        db.commit()
        logger.info("[Webhook] EmailLog %d: %s → %s", email_log.id, email_log.status, new_status)

        # Mirror the event into the PostHog event stream so it can be combined with
        # demo events in funnels. distinct_id = the prospect's demo slug → same person
        # as the demo capture. Best-effort (capture never raises).
        demo_slug: str | None = _resolve_demo_slug(db, email_log)
        distinct_id: str = demo_slug or (
            f"prospect_{email_log.prospect_id}"
            if email_log.prospect_id
            else f"email_{email_log.recipient_email}"
        )
        await posthog_service.capture(
            distinct_id=distinct_id,
            event=event_type.replace(".", "_"),  # "email.opened" → "email_opened"
            properties={
                "demo_slug": demo_slug,
                "prospect_id": email_log.prospect_id,
                "campaign_id": email_log.campaign_id,
                "ab_variant": email_log.ab_variant,
                "email_log_id": email_log.id,
                "$lib": "devleadhunter-api",
            },
            timestamp=now.isoformat(),
        )


# ---------------------------------------------------------------------------
# Storyblok — sync client-published edits back into content_json
# ---------------------------------------------------------------------------


def _verify_storyblok_signature(body: bytes, signature: str) -> bool:
    """
    Verify the Storyblok ``webhook-signature`` header (HMAC-SHA1 of the body).

    Returns ``True`` when no secret is configured — the endpoint is safe by
    design: the payload is never trusted, the story is always re-fetched from
    Storyblok with the site's own token, so a forged request can only trigger
    a resync from the source of truth.
    """
    secret: str = getattr(settings, "storyblok_webhook_secret", None) or ""
    if not secret:
        return True
    expected: str = hmac.new(secret.encode(), body, hashlib.sha1).hexdigest()
    return hmac.compare_digest(signature, expected)


@router.post("/storyblok", status_code=status.HTTP_204_NO_CONTENT)
async def storyblok_webhook(
    request: Request,
    webhook_signature: str = Header(default="", alias="webhook-signature"),
    db: Session = Depends(get_db),
) -> None:
    """
    Receive Storyblok publish events and refresh ``demo_site.content_json``.

    The public site (demo AND delivered domain) renders ``content_json`` — this
    webhook is what makes the CMS functional for the client: whenever they hit
    "Publish" in their space, the published story is re-fetched (CDN API,
    ``version=published``, the site's own public token) and flattened back into
    the ``SiteContent`` shape stored in the database.

    Registered per space at provisioning (``_register_publish_webhook``).
    """
    body: bytes = await request.body()

    if not _verify_storyblok_signature(body, webhook_signature):
        logger.warning("[Webhook] Invalid Storyblok signature — request rejected")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    try:
        payload: dict[str, Any] = json.loads(body)
    except json.JSONDecodeError as exc:
        logger.warning("[Webhook] Malformed Storyblok JSON body: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        ) from exc

    action: str = str(payload.get("action", ""))
    space_id_raw: Any = payload.get("space_id")
    full_slug: str = str(payload.get("full_slug", "") or "")

    logger.info("[Webhook] Storyblok action=%s space_id=%s slug=%s", action, space_id_raw, full_slug)

    # Only story publications matter; sites have a single "home" story.
    if action and action != "published":
        return
    if full_slug and full_slug != "home":
        return
    if not isinstance(space_id_raw, int):
        try:
            space_id_raw = int(space_id_raw)
        except (TypeError, ValueError):
            return

    site: DemoSite | None = db.execute(
        select(DemoSite)
        .where(
            DemoSite.storyblok_space_id == space_id_raw,
            DemoSite.status != DemoSiteStatus.DELETED.value,
        )
        .order_by(DemoSite.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if site is None:
        logger.info("[Webhook] Storyblok space %s has no matching demo site", space_id_raw)
        return
    if not site.storyblok_public_token:
        logger.warning("[Webhook] Demo site %d has no Storyblok public token — cannot sync", site.id)
        return

    # Never trust the payload — re-fetch the PUBLISHED story from Storyblok.
    story_content = await storyblok_service.fetch_published_home_content(site.storyblok_public_token)
    if story_content is None:
        logger.warning("[Webhook] Could not fetch published story for demo site %d", site.id)
        return

    flat_content = from_storyblok_site_content(story_content)
    if flat_content is None:
        logger.warning(
            "[Webhook] Published story for demo site %d carries no site_content blok — skipped",
            site.id,
        )
        return

    site.content_json = flat_content
    db.commit()
    logger.info("[Webhook] Demo site %d content_json synced from Storyblok space %s", site.id, space_id_raw)
