"""
Public ingestion endpoint for live demo / video behavioural events.

The demo-host (a separate domain) beacons a prospect's key actions here so the
owner gets a real-time mobile push. Unauthenticated by design — the demo-host has
no user session; the slug resolves to its owning user (a demo site, or a receptionist
for its video page's events). Unknown slugs are ignored.
"""

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from models.demo_site_lead import LEAD_STATUS_DRAFT, LEAD_STATUS_SUBMITTED, DemoSiteLead
from schemas.notification import DemoEventIn
from services.ai_assistant.assistant_service import ai_assistant_service
from services.notification_service import notification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo-events", tags=["demo-events"])

# Banner exits that carry an unsent draft: the prospect typed a message then left
# without clicking « Je suis intéressé ». Captured so their words are never lost.
_DRAFT_EVENTS: frozenset[str] = frozenset({"demo_cta_banner_collapse", "demo_cta_banner_abandoned"})

# The receptionist's video page (/va) beacons under its own prefix: its slug names an assistant, not a demo site.
_ASSISTANT_VIDEO_EVENT_PREFIX = "assistant_video_"


def _persist_submitted_lead(db: Session, site: DemoSite, message: str | None) -> None:
    """Persist a real lead — the prospect clicked « Je suis intéressé »."""
    try:
        db.add(
            DemoSiteLead(
                user_id=site.user_id,
                prospect_id=site.prospect_id,
                demo_site_id=site.id,
                message=message,
                status=LEAD_STATUS_SUBMITTED,
            )
        )
        db.commit()
    except Exception as exc:
        # The notification still goes out: losing the durable row must not
        # swallow the strongest funnel signal there is.
        logger.warning("demo_lead persist failed (slug=%s): %s", site.slug, exc)
        db.rollback()


def _persist_draft(db: Session, site: DemoSite, message: str) -> None:
    """Upsert the prospect's unsent draft so their words are never lost.

    One draft per demo site: the latest text wins (a prospect may collapse then
    abandon in one visit), and a real submitted lead is never touched.
    """
    try:
        existing = (
            db.execute(
                select(DemoSiteLead)
                .where(DemoSiteLead.demo_site_id == site.id, DemoSiteLead.status == LEAD_STATUS_DRAFT)
                .order_by(DemoSiteLead.created_at.desc())
            )
            .scalars()
            .first()
        )
        if existing is not None:
            existing.message = message
        else:
            db.add(
                DemoSiteLead(
                    user_id=site.user_id,
                    prospect_id=site.prospect_id,
                    demo_site_id=site.id,
                    message=message,
                    status=LEAD_STATUS_DRAFT,
                )
            )
        db.commit()
    except Exception as exc:
        logger.warning("demo draft persist failed (slug=%s): %s", site.slug, exc)
        db.rollback()


async def _notify_assistant_video_event(db: Session, payload: DemoEventIn) -> None:
    """Notify the owner of an event on a receptionist's prospection video page; unknown slugs are ignored."""
    assistant = ai_assistant_service.get_by_slug(db, payload.demo_slug)
    if assistant is None:
        return
    await notification_service.notify_assistant_video_event(
        db,
        user_id=assistant.user_id,
        prospect_id=assistant.prospect_id,
        event_name=payload.event,
        fallback_name=assistant.slug,
        channel=payload.channel,
    )


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def ingest_demo_event(payload: DemoEventIn, db: Session = Depends(get_db)) -> None:
    """
    Receive a behavioural event from a live demo/video page and notify the owner.

    The prospect's own words must outlive the 90-day notification log, so they are
    persisted as a durable ``DemoSiteLead`` before notifying: a ``demo_lead`` (the
    « Ce site vous plaît ? » banner clicked) as a real ``submitted`` lead, and an
    unsent message left on ``collapse``/``abandoned`` as a ``draft``.

    Args:
        payload: The beaconed event (slug + event name + optional context).
        db: Database session.
    """
    if payload.event.startswith(_ASSISTANT_VIDEO_EVENT_PREFIX):
        await _notify_assistant_video_event(db, payload)
        return
    site = db.execute(
        select(DemoSite).where(
            DemoSite.slug == payload.demo_slug,
            DemoSite.status != DemoSiteStatus.DELETED.value,
        )
    ).scalar_one_or_none()
    if site is None:
        return
    message = (payload.message or "").strip() or None
    if payload.event == "demo_lead":
        _persist_submitted_lead(db, site, message)
    elif payload.event in _DRAFT_EVENTS and message:
        _persist_draft(db, site, message)
    await notification_service.notify_demo_event(
        db,
        user_id=site.user_id,
        prospect_id=site.prospect_id,
        event_name=payload.event,
        fallback_name=site.slug,
        label=payload.label,
        host=payload.host,
        seconds=payload.seconds,
        max_scroll=payload.max_scroll,
        message=payload.message,
        channel=payload.channel,
    )
