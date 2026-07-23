"""
Shared PostHog identity resolution for a prospect.

The demo slug is the identity used by demo-site tracking: ``useDemoTracking``
initialises PostHog with ``distinctID = slug``. Mirroring email events under the
SAME identity is what lets PostHog stitch the ``email → démo → vente`` funnel
onto a single person (and attach the demo session replay to it).

This module is the single source of truth for that mapping so the send path
(``email_sending_service``) and the Resend webhook (``webhooks``) always agree
on which ``distinct_id`` an email event carries.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite


class DemoIdentityResolver:
    """Resolves PostHog distinct IDs from demo slugs and prospect metadata."""

    @staticmethod
    def resolve_demo_slug(db: Session, user_id: int, prospect_id: Optional[int]) -> Optional[str]:
        """
        Return the prospect's most recent non-deleted demo slug (PostHog identity).

        Args:
            db: Active database session.
            user_id: Owner of the demo site (scoping — never leak another user's data).
            prospect_id: Prospect whose demo slug we want (None → no slug).

        Returns:
            The newest live demo slug for the prospect, or None when absent.
        """
        if not prospect_id:
            return None
        site = db.execute(
            select(DemoSite)
            .where(
                DemoSite.prospect_id == prospect_id,
                DemoSite.user_id == user_id,
                DemoSite.status != DemoSiteStatus.DELETED.value,
            )
            .order_by(DemoSite.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        return site.slug if site else None

    @staticmethod
    def posthog_distinct_id(
        demo_slug: Optional[str], prospect_id: Optional[int], recipient_email: str = ""
    ) -> str:
        """
        Resolve the PostHog ``distinct_id`` for an email event.

        Prefer the demo slug (= the demo-site tracking identity) so the email and
        demo events resolve to the same person. Fall back to a stable per-prospect
        id, then the recipient address, so an event is never dropped for lack of a
        slug (a prospect without a demo yet still gets a coherent timeline).

        Args:
            demo_slug: The prospect's demo slug, when it has a live demo.
            prospect_id: Prospect id, used for the fallback identity.
            recipient_email: Recipient address, last-resort identity.

        Returns:
            A non-empty distinct id.
        """
        if demo_slug:
            return demo_slug
        if prospect_id:
            return f"prospect_{prospect_id}"
        return f"email_{recipient_email}"


def resolve_demo_slug(db: Session, user_id: int, prospect_id: Optional[int]) -> Optional[str]:
    """Backward-compatible wrapper around ``DemoIdentityResolver.resolve_demo_slug``."""
    return DemoIdentityResolver.resolve_demo_slug(db, user_id, prospect_id)


def posthog_distinct_id(
    demo_slug: Optional[str], prospect_id: Optional[int], recipient_email: str = ""
) -> str:
    """Backward-compatible wrapper around ``DemoIdentityResolver.posthog_distinct_id``."""
    return DemoIdentityResolver.posthog_distinct_id(demo_slug, prospect_id, recipient_email)
