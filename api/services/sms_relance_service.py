"""Find prospects to SMS (relance or cold) and send, reviving the demo if dormant.

The SMS pushes a prospect back to their demo site. Two selections:
- **Relance**: a prospect emailed a while ago who did NOT react (no human open, click
  or reply), owns a mobile, was never texted or opted out. More natural than a cold SMS.
- **Cold**: a prospect with a mobile but NO email — the SMS is the first touch.

A prospect's demo may have gone dormant (EXPIRED) since its 21-day TTL lapsed; the send
revives it (from ``content_json``, no re-scrape) and restarts a fresh 21-day TTL, so the
prospect always gets a live link.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from models.sms_message import SmsMessage
from services.demo_site_service import demo_site_service
from services.sms.phone_normalizer import is_mobile_fr, to_e164_fr
from services.sms_config_service import sms_config_service
from services.sms_service import sms_service
from services.tracking_links import sms_tracked_link

logger = logging.getLogger(__name__)

# A prospect qualifies for a relance this many *calendar* days after the email.
DEFAULT_RELANCE_AFTER_DAYS: int = 30

# A demo the SMS can point at: live, or dormant (revivable on send).
_REACHABLE_DEMO_STATUSES: list[str] = [DemoSiteStatus.ACTIVE.value, DemoSiteStatus.EXPIRED.value]


class SmsRelanceCandidate:
    """A prospect to SMS, with the (possibly dormant) demo to push."""

    def __init__(
        self,
        *,
        prospect: ProspectDB,
        demo_site: DemoSite,
        demo_url: str,
        emailed_at: datetime | None = None,
        cold: bool = False,
    ) -> None:
        self.prospect = prospect
        self.demo_site = demo_site
        self.demo_url = demo_url
        self.emailed_at = emailed_at
        self.cold = cold


class SmsRelanceService:
    """Select prospects to SMS (relance + cold) and send, reviving dormant demos."""

    def find_candidates(
        self,
        db: Session,
        user_id: int,
        *,
        after_days: int = DEFAULT_RELANCE_AFTER_DAYS,
        limit: int = 50,
    ) -> list[SmsRelanceCandidate]:
        """Return the user's prospects already due for an SMS relance (emailed, no reaction).

        Used by the worker to actually send: only prospects whose first email is older
        than *after_days* qualify.

        Args:
            db: Active database session.
            user_id: Owner.
            after_days: Minimum age (days) of the unanswered email.
            limit: Max candidates to return.

        Returns:
            Eligible candidates, oldest email first.
        """
        cutoff = datetime.utcnow() - timedelta(days=after_days)
        return self._collect_relance(db, user_id, cutoff=cutoff, limit=limit)

    def find_relance_projection_candidates(
        self, db: Session, user_id: int, *, limit: int = 500
    ) -> list[SmsRelanceCandidate]:
        """Return every relance-destined prospect regardless of email age, for the forecast.

        Unlike :meth:`find_candidates`, there is no age cutoff: a prospect emailed
        recently is returned too, carrying its first-email date so the forecast can
        place the SMS at ``emailed_at + delay`` — the send that is *planned*, not yet due.

        Args:
            db: Active database session.
            user_id: Owner.
            limit: Max candidates to return.

        Returns:
            Relance-destined candidates, oldest email first.
        """
        return self._collect_relance(db, user_id, cutoff=None, limit=limit)

    def _collect_relance(
        self, db: Session, user_id: int, *, cutoff: datetime | None, limit: int
    ) -> list[SmsRelanceCandidate]:
        """Select prospects with an unanswered email, a mobile, a demo, never texted.

        Args:
            db: Active database session.
            user_id: Owner.
            cutoff: When set, keep only emails sent at or before it (worker path); when
                ``None``, keep every age (forecast projection path).
            limit: Max candidates to return.

        Returns:
            Matching candidates, oldest email first.
        """
        conditions = [
            EmailLog.user_id == user_id,
            EmailLog.prospect_id.isnot(None),
            EmailLog.sent_at.isnot(None),
            EmailLog.opened_at.is_(None),
            EmailLog.clicked_at.is_(None),
            EmailLog.replied_at.is_(None),
        ]
        if cutoff is not None:
            conditions.append(EmailLog.sent_at <= cutoff)
        unreacted = (
            select(EmailLog.prospect_id, func.min(EmailLog.sent_at).label("emailed_at"))
            .where(*conditions)
            .group_by(EmailLog.prospect_id)
            .subquery()
        )
        already_texted = select(SmsMessage.prospect_id).where(SmsMessage.user_id == user_id).subquery()

        rows = db.execute(
            select(ProspectDB, unreacted.c.emailed_at)
            .join(unreacted, unreacted.c.prospect_id == ProspectDB.id)
            .where(
                ProspectDB.user_id == user_id,
                ProspectDB.phone.isnot(None),
                ProspectDB.id.notin_(select(already_texted.c.prospect_id)),
            )
            .order_by(unreacted.c.emailed_at.asc())
            .limit(limit * 3)  # over-fetch: mobile/demo/suppression filters trim below
        ).all()

        candidates: list[SmsRelanceCandidate] = []
        for prospect, emailed_at in rows:
            candidate = self._build_candidate(db, user_id, prospect, emailed_at=emailed_at, cold=False)
            if candidate is not None:
                candidates.append(candidate)
            if len(candidates) >= limit:
                break
        return candidates

    def find_cold_candidates(self, db: Session, user_id: int, *, limit: int = 50) -> list[SmsRelanceCandidate]:
        """Return the user's prospects for a cold SMS (a mobile but no email).

        Args:
            db: Active database session.
            user_id: Owner.
            limit: Max candidates to return.

        Returns:
            Eligible cold candidates.
        """
        already_texted = select(SmsMessage.prospect_id).where(SmsMessage.user_id == user_id).subquery()
        rows = db.execute(
            select(ProspectDB)
            .where(
                ProspectDB.user_id == user_id,
                ProspectDB.phone.isnot(None),
                or_(ProspectDB.email.is_(None), ProspectDB.email == ""),
                ProspectDB.id.notin_(select(already_texted.c.prospect_id)),
            )
            .order_by(ProspectDB.created_at.asc())
            .limit(limit * 3)
        ).all()

        candidates: list[SmsRelanceCandidate] = []
        for (prospect,) in rows:
            candidate = self._build_candidate(db, user_id, prospect, emailed_at=None, cold=True)
            if candidate is not None:
                candidates.append(candidate)
            if len(candidates) >= limit:
                break
        return candidates

    def _build_candidate(
        self, db: Session, user_id: int, prospect: ProspectDB, *, emailed_at: datetime | None, cold: bool
    ) -> SmsRelanceCandidate | None:
        """Turn a prospect into a candidate when it is SMS-reachable with a demo, else ``None``."""
        if not is_mobile_fr(prospect.phone):
            return None
        if prospect.do_not_contact:
            return None
        to_e164 = to_e164_fr(prospect.phone)
        if to_e164 and sms_service.is_suppressed(db, user_id, to_e164):
            return None
        site = self.demo_for_prospect(db, user_id, prospect.id)
        if site is None:
            return None
        demo_url = sms_tracked_link(demo_site_service.demo_url_for_slug(site.slug))
        return SmsRelanceCandidate(
            prospect=prospect, demo_site=site, demo_url=demo_url, emailed_at=emailed_at, cold=cold
        )

    def demo_for_prospect(self, db: Session, user_id: int, prospect_id: int) -> DemoSite | None:
        """The prospect's newest reachable demo (ACTIVE, else dormant EXPIRED), or ``None``."""
        return (
            db.query(DemoSite)
            .filter(
                DemoSite.user_id == user_id,
                DemoSite.prospect_id == prospect_id,
                DemoSite.status.in_(_REACHABLE_DEMO_STATUSES),
                DemoSite.slug.isnot(None),
            )
            .order_by(DemoSite.created_at.desc())
            .first()
        )

    async def send_relance(self, db: Session, user_id: int, candidate: SmsRelanceCandidate) -> bool:
        """Send one SMS (relance or cold) — revive a dormant demo first, then restart its TTL.

        Args:
            db: Active database session.
            user_id: Sender.
            candidate: The eligible candidate.

        Returns:
            ``True`` when the SMS was accepted by the provider.
        """
        config = sms_config_service.get(db, user_id)
        if config is None:
            return False
        if candidate.demo_site.status == DemoSiteStatus.EXPIRED.value:
            await demo_site_service.revive_demo_site(db, candidate.demo_site)
        outcome = await sms_service.send_to_prospect(
            db,
            user_id=user_id,
            prospect=candidate.prospect,
            config=config,
            demo_url=candidate.demo_url,
            cold=candidate.cold,
        )
        if outcome.sent:
            # A fresh 21-day TTL from the SMS send — the prospect gets a live link again.
            demo_site_service.restart_demo_ttl(db, candidate.demo_site, datetime.now(UTC))
        return outcome.sent


sms_relance_service = SmsRelanceService()
