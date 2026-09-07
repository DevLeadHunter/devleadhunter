"""
Webhook endpoint for Resend email events.

Configure in your Resend dashboard:
  URL: https://your-api.com/api/v1/webhooks/resend
  Events: email.sent, email.delivered, email.opened, email.clicked,
          email.bounced, email.complained, email.received (reply capture)

Resend signs each request with a ``svix-signature`` header.
Set RESEND_WEBHOOK_SECRET in your .env to enable signature verification.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime
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
from models.prospect_db import ProspectDB
from models.resend_config import ResendConfig
from services import reply_capture_service
from services.activity_log_service import CATEGORY_DEMO_SITE, STATUS_INFO, activity_log_service
from services.bounce_fallback_service import bounce_fallback_service
from services.demo_identity import posthog_distinct_id, resolve_demo_slug
from services.encryption_service import encryption_service
from services.notification_service import notification_service
from services.posthog_service import posthog_service
from services.storyblok_service import storyblok_service
from services.templates.site_content import from_storyblok_site_content

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


# Complete map of all Resend email webhook event types → EmailStatus.
# Sources: https://resend.com/docs/dashboard/webhooks/event-types
_EVENT_STATUS_MAP: dict[str, str] = {
    "email.scheduled": EmailStatus.SCHEDULED.value,
    "email.sent": EmailStatus.SENT.value,
    "email.delivered": EmailStatus.DELIVERED.value,
    "email.delivery_delayed": EmailStatus.DELIVERY_DELAYED.value,
    "email.opened": EmailStatus.OPENED.value,
    "email.clicked": EmailStatus.CLICKED.value,
    "email.bounced": EmailStatus.BOUNCED.value,
    "email.complained": EmailStatus.COMPLAINED.value,
    "email.failed": EmailStatus.FAILED.value,
    "email.suppressed": EmailStatus.SUPPRESSED.value,
    # email.received (inbound reply capture) is handled separately — see reply_capture_service.
}

# Maps each event type to the EmailLog timestamp column it populates.
_EVENT_TIMESTAMP_MAP: dict[str, str] = {
    "email.sent": "sent_at",
    "email.delivered": "delivered_at",
    "email.delivery_delayed": "delivered_at",
    "email.opened": "opened_at",
    "email.clicked": "clicked_at",
    "email.bounced": "bounced_at",
    "email.complained": "complained_at",
    "email.failed": "failed_at",
    "email.suppressed": "suppressed_at",
    # email.scheduled has no dedicated timestamp column.
}

# Events whose payload carries a human failure reason worth storing on the log.
_FAILURE_EVENTS: frozenset[str] = frozenset({"email.bounced", "email.failed", "email.complained"})


def _extract_failure_reason(data: dict[str, Any]) -> str | None:
    """Pull the human failure reason from a Resend bounce/failed/complained payload, or None."""
    bounce = data.get("bounce")
    if isinstance(bounce, dict):
        message = (bounce.get("message") or "").strip()
        sub_type = (bounce.get("subType") or bounce.get("sub_type") or "").strip()
        if message:
            return f"{message} ({sub_type})" if sub_type else message
        if sub_type:
            return sub_type
    failed = data.get("failed")
    if isinstance(failed, dict):
        reason = (failed.get("reason") or "").strip()
        if reason:
            return reason
    reason = (data.get("reason") or "").strip()
    return reason or None


# Numeric rank used to prevent status from moving backwards on late/duplicate
# webhook deliveries.  Equal-rank statuses do NOT overwrite each other
# (strict ``>`` comparison).
_STATUS_RANK: dict[str, int] = {
    EmailStatus.PENDING.value: 0,
    EmailStatus.SENDING.value: 1,
    EmailStatus.SCHEDULED.value: 1,
    EmailStatus.SENT.value: 2,
    EmailStatus.DELIVERY_DELAYED.value: 3,
    EmailStatus.DELIVERED.value: 4,
    EmailStatus.OPENED.value: 5,
    EmailStatus.CLICKED.value: 6,
    EmailStatus.BOUNCED.value: 7,
    EmailStatus.COMPLAINED.value: 7,
    EmailStatus.FAILED.value: 7,
    EmailStatus.SUPPRESSED.value: 7,
    # A captured reply is the strongest signal — nothing may overwrite it.
    EmailStatus.REPLIED.value: 8,
}

# An ``email.opened`` landing within this many seconds of delivery is a machine
# prefetch (Gmail image proxy / security scanner), not a human read. The open
# payload carries no user-agent, so timing from delivery is the only discriminator.
_MACHINE_OPEN_WINDOW_SECONDS: int = 60


def _signature_matches(
    body: bytes,
    svix_id: str,
    svix_timestamp: str,
    svix_signature: str,
    secret: str,
) -> bool:
    """
    Return ``True`` when *svix_signature* is valid for *body* under *secret*.

    Args:
        body:           Raw request body bytes.
        svix_id:        Value of the ``svix-id`` request header.
        svix_timestamp: Value of the ``svix-timestamp`` request header.
        svix_signature: Value of the ``svix-signature`` request header.
        secret:         Resend webhook signing secret (``whsec_…``).

    Returns:
        ``True`` when the signature matches.
    """
    if not secret:
        return False

    signed_content: bytes = f"{svix_id}.{svix_timestamp}.".encode() + body

    raw_secret: str = secret.removeprefix("whsec_")
    try:
        key: bytes = base64.b64decode(raw_secret)
    except Exception:
        key = raw_secret.encode()

    expected_digest: bytes = hmac.new(key, signed_content, hashlib.sha256).digest()
    expected_b64: str = base64.b64encode(expected_digest).decode()

    for sig in svix_signature.split(" "):
        clean = sig.split(",", 1)[-1]
        if hmac.compare_digest(clean, expected_b64):
            return True
    return False


def _find_email_log_for_payload(db: Session, data: dict[str, Any]) -> EmailLog | None:
    """
    Locate the ``EmailLog`` row targeted by a Resend webhook payload.

    Args:
        db:   Active database session.
        data: The ``data`` object from the webhook body.

    Returns:
        The matching row, or ``None`` when not found.
    """
    email_log: EmailLog | None = None
    resend_message_id: str = data.get("email_id", "")

    raw_id: str | None = _read_tag(data.get("tags"), "email_log_id")
    if raw_id:
        try:
            email_log = db.execute(select(EmailLog).where(EmailLog.id == int(raw_id))).scalar_one_or_none()
        except (ValueError, TypeError):
            logger.warning("[Webhook] Non-integer email_log_id tag value: %r", raw_id)

    if email_log is None and resend_message_id:
        email_log = db.execute(
            select(EmailLog).where(EmailLog.provider_message_id == resend_message_id)
        ).scalar_one_or_none()

    return email_log


def _webhook_secrets_for_payload(db: Session, data: dict[str, Any]) -> list[str]:
    """
    Collect webhook signing secrets that may have signed this event.

    Per-user secrets are tried first (multi-tenant Resend accounts), then the
    platform ``RESEND_WEBHOOK_SECRET`` from ``.env`` as a legacy fallback.

    Args:
        db:   Active database session.
        data: The ``data`` object from the webhook body.

    Returns:
        De-duplicated list of raw signing secrets to try.
    """
    secrets: list[str] = []
    seen: set[str] = set()

    def _add(secret: str | None) -> None:
        if secret and secret not in seen:
            seen.add(secret)
            secrets.append(secret)

    email_log = _find_email_log_for_payload(db, data)
    if email_log is not None:
        config: ResendConfig | None = db.execute(
            select(ResendConfig).where(ResendConfig.user_id == email_log.user_id)
        ).scalar_one_or_none()
        if config is not None and config.webhook_secret:
            _add(encryption_service.decrypt(config.webhook_secret))

    _add(getattr(settings, "resend_webhook_secret", "") or None)
    return secrets


def _verify_signature(
    body: bytes,
    svix_id: str,
    svix_timestamp: str,
    svix_signature: str,
    secrets: list[str],
) -> bool:
    """
    Verify the Svix webhook signature used by Resend.

    Returns ``True`` when the signature is valid for any candidate secret.
    Also returns ``True`` when no secret is configured anywhere so that local
    development works without a webhook secret (never do this in production).

    Args:
        body:           Raw request body bytes (already buffered).
        svix_id:        Value of the ``svix-id`` request header.
        svix_timestamp: Value of the ``svix-timestamp`` request header.
        svix_signature: Value of the ``svix-signature`` request header.
        secrets:        Signing secrets to try (per-user, then platform fallback).

    Returns:
        ``True`` if the signature is valid or no secret is configured.
    """
    if not secrets:
        return True  # Dev mode — no secret configured

    return any(_signature_matches(body, svix_id, svix_timestamp, svix_signature, secret) for secret in secrets)


def _read_tag(tags: object, name: str) -> str | None:
    """
    Read a Resend tag, whichever shape the payload uses.

    Resend accepts ``[{"name": …, "value": …}]`` when sending but echoes back a flat
    ``{"name": "value"}`` object in webhooks. Assuming a single shape raised an
    AttributeError on every tagged event, which surfaced as a 500 and endless retries.

    Args:
        tags: The ``tags`` field of the payload, in either shape.
        name: Tag to read.

    Returns:
        The tag value, or None when absent or unreadable.
    """
    if isinstance(tags, dict):
        value = tags.get(name)
        return str(value) if value is not None else None
    if isinstance(tags, list):
        for entry in tags:
            if isinstance(entry, dict) and entry.get("name") == name:
                value = entry.get("value")
                return str(value) if value is not None else None
    return None


def _parse_event_time(payload: dict[str, Any], data: dict[str, Any]) -> datetime:
    """
    Return the event's own timestamp as naive UTC, falling back to now.

    Reading the payload timestamp (not the receive time) keeps machine/human open
    classification correct even when Resend retries a webhook long after the event.

    Args:
        payload: The full webhook body.
        data:    The ``data`` object of the webhook body.

    Returns:
        The event time as a naive UTC ``datetime``.
    """
    raw = data.get("created_at") or payload.get("created_at")
    if isinstance(raw, str):
        normalized = raw.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(UTC).replace(tzinfo=None)
            return parsed
    return datetime.now(UTC).replace(tzinfo=None)


def _is_machine_open(event_time: datetime, baseline: datetime | None) -> bool:
    """
    True when an open landed within the prefetch window of delivery — a machine open.

    Gmail's image proxy and security scanners fetch the tracking pixel at delivery,
    seconds after ``baseline`` (delivered_at, else sent_at). A human read lands
    meaningfully later. With no baseline to compare against, err towards human so a
    real open is never dropped.

    Args:
        event_time: The open event time (naive UTC).
        baseline: Delivery (or send) time to measure the delay from (naive UTC).

    Returns:
        ``True`` when the open is a machine prefetch.
    """
    if baseline is None:
        return False
    return (event_time - baseline).total_seconds() <= _MACHINE_OPEN_WINDOW_SECONDS


async def _handle_open_event(
    db: Session,
    email_log: EmailLog,
    payload: dict[str, Any],
    data: dict[str, Any],
    resend_message_id: str,
) -> None:
    """
    Record a Resend ``email.opened`` event, separating machine prefetch from human reads.

    A pixel fetch within ``_MACHINE_OPEN_WINDOW_SECONDS`` of delivery is a
    machine open (Gmail proxy / scanner): it is stored on ``machine_opened_at``
    but never advances status, notifies or scores. Opens landing meaningfully
    after delivery are human: they bump ``open_count`` and notify on every reopen
    (a strong warm-lead signal). Only the first human open is mirrored to PostHog,
    to keep the funnel step clean.

    Args:
        db: Active database session.
        email_log: The row the event targets.
        payload: The full webhook body (for the event timestamp).
        data: The ``data`` object (for the event timestamp).
        resend_message_id: Provider message id, backfilled when missing.
    """
    event_time: datetime = _parse_event_time(payload, data)
    baseline: datetime | None = email_log.delivered_at or email_log.sent_at

    if _is_machine_open(event_time, baseline):
        if email_log.machine_opened_at is None:
            email_log.machine_opened_at = event_time
            db.commit()
        return

    email_log.open_count = (email_log.open_count or 0) + 1
    email_log.last_open_at = event_time
    first_human_open: bool = email_log.opened_at is None
    if first_human_open:
        email_log.opened_at = event_time
    if _STATUS_RANK[EmailStatus.OPENED.value] > _STATUS_RANK.get(email_log.status, 0):
        email_log.status = EmailStatus.OPENED.value
    if resend_message_id and not email_log.provider_message_id:
        email_log.provider_message_id = resend_message_id
    db.commit()
    logger.info("[Webhook] EmailLog %d: human open #%d", email_log.id, email_log.open_count)

    if first_human_open:
        demo_slug: str | None = resolve_demo_slug(db, email_log.user_id, email_log.prospect_id)
        await posthog_service.capture(
            distinct_id=posthog_distinct_id(demo_slug, email_log.prospect_id, email_log.recipient_email),
            event="email_opened",
            properties={
                "demo_slug": demo_slug,
                "prospect_id": email_log.prospect_id,
                "campaign_id": email_log.campaign_id,
                "ab_variant": email_log.ab_variant,
                "email_log_id": email_log.id,
                "$lib": "devleadhunter-api",
            },
            timestamp=event_time.isoformat(),
        )

    await notification_service.notify_email_event(
        db,
        user_id=email_log.user_id,
        event_name="email_opened",
        recipient_email=email_log.recipient_email,
        prospect_id=email_log.prospect_id,
        subject=email_log.subject,
        email_log_id=email_log.id,
        open_count=email_log.open_count,
    )


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

    try:
        payload: dict[str, Any] = json.loads(body)
    except json.JSONDecodeError as exc:
        logger.warning("[Webhook] Malformed JSON body: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        ) from exc

    data: dict[str, Any] = payload.get("data", {})
    secrets: list[str] = _webhook_secrets_for_payload(db, data)

    if not _verify_signature(body, svix_id, svix_timestamp, svix_signature, secrets):
        logger.warning("[Webhook] Invalid Resend signature — request rejected")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    event_type: str = payload.get("type", "")

    logger.info("[Webhook] Resend event=%s message_id=%s", event_type, data.get("email_id"))

    # Inbound reply on the capture domain — its own pipeline (token matching,
    # body fetch, REPLIED status, notification), see reply_capture_service.
    if event_type == "email.received":
        await reply_capture_service.handle_received(db, data)
        return

    if event_type not in _EVENT_STATUS_MAP:
        # Unknown / unsubscribed event — acknowledge without error so Resend
        # does not retry delivery.
        return

    resend_message_id: str = data.get("email_id", "")

    # --- Locate the matching EmailLog row -----------------------------------

    email_log: EmailLog | None = _find_email_log_for_payload(db, data)

    if email_log is None:
        logger.warning(
            "[Webhook] No EmailLog found for event=%s message_id=%s",
            event_type,
            resend_message_id,
        )
        return  # Acknowledge — nothing to update

    # Opens need machine-vs-human classification and per-open counting, so they
    # bypass the linear status ladder below.
    if event_type == "email.opened":
        await _handle_open_event(db, email_log, payload, data, resend_message_id)
        return

    # --- Advance status (never downgrade) -----------------------------------

    new_status: str = _EVENT_STATUS_MAP[event_type]
    ts_col: str | None = _EVENT_TIMESTAMP_MAP.get(event_type)
    now: datetime = datetime.now(UTC).replace(tzinfo=None)  # naive UTC to match DB columns

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
        if event_type in _FAILURE_EVENTS:
            reason: str | None = _extract_failure_reason(data)
            if reason:
                email_log.error_message = reason
        db.commit()
        logger.info("[Webhook] EmailLog %d: %s → %s", email_log.id, email_log.status, new_status)

        # A hard bounce on the primary email → re-route to the prospect's next email (multi-email fallback).
        if new_status == EmailStatus.BOUNCED.value:
            bounce_fallback_service.handle_bounce(db, email_log)

        # A delivery on any address clears a stale « email injoignable » flag (a fallback
        # or a hand-fixed address finally landed) — the prospect is reachable by email again.
        if new_status == EmailStatus.DELIVERED.value and email_log.prospect_id:
            prospect_row = db.get(ProspectDB, email_log.prospect_id)
            if prospect_row is not None and prospect_row.email_undeliverable:
                bounce_fallback_service.clear_undeliverable(db, prospect_row)
                db.commit()

        # Mirror the event into the PostHog event stream so it can be combined with
        # demo events in funnels. distinct_id = the prospect's demo slug → same person
        # as the demo capture. Best-effort (capture never raises).
        # NOTE: email.sent is set to SENT synchronously by the send path, so this
        # webhook receives it at an equal rank and never reaches here for "sent" —
        # that first funnel step is emitted at the source (email_sending_service).
        demo_slug: str | None = resolve_demo_slug(db, email_log.user_id, email_log.prospect_id)
        await posthog_service.capture(
            distinct_id=posthog_distinct_id(demo_slug, email_log.prospect_id, email_log.recipient_email),
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

        # Mirror the event into a mobile push notification (best-effort).
        await notification_service.notify_email_event(
            db,
            user_id=email_log.user_id,
            event_name=event_type.replace(".", "_"),
            recipient_email=email_log.recipient_email,
            prospect_id=email_log.prospect_id,
            subject=email_log.subject,
            email_log_id=email_log.id,
        )


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

    # Metrics injected by the API (address, Google rating/count, map coords) are not editable Storyblok
    # sections, so the flattened story doesn't carry them — preserve them from the previous content_json,
    # otherwise the address, the Google badge and the map would vanish on the client's first publish.
    previous = site.content_json if isinstance(site.content_json, dict) else {}
    for key in ("address", "rating", "reviewsCount", "lat", "lng"):
        if key not in flat_content and previous.get(key) is not None:
            flat_content[key] = previous[key]

    site.content_json = flat_content
    db.commit()
    logger.info("[Webhook] Demo site %d content_json synced from Storyblok space %s", site.id, space_id_raw)
    activity_log_service.record(
        category=CATEGORY_DEMO_SITE,
        action="cms_published",
        status=STATUS_INFO,
        title=f"Contenu CMS publié · {site.business_name}",
        user_id=site.user_id,
        entity_type="demo_site",
        entity_id=site.id,
    )
