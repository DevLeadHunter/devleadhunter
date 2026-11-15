"""
A first email that bounces and is re-sent to the prospect's next address must not leave two follow-ups behind:
the ones armed by the bounced send are held back, and the re-sent first email arms its own when it leaves.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.campaign import Campaign, CampaignStatus
from models.email_log import EmailLog
from models.email_queue import EmailQueue
from models.prospect_db import ProspectDB
from services.bounce_fallback_service import BounceFallbackService
from services.campaign_queue_service import CampaignQueueService

_USER_ID = 7
_HELD_BACK_REASON = "Premier mail rejeté, relance replanifiée après le renvoi"
_IN_THREE_DAYS: datetime = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=3)


def _prospect(db: Session, name: str, emails: list[str]) -> ProspectDB:
    prospect = ProspectDB(
        user_id=_USER_ID, name=name, category="Paysagiste", source="google_maps", email=emails[0], emails=emails
    )
    db.add(prospect)
    db.flush()
    return prospect


def _campaign(db: Session, name: str) -> Campaign:
    campaign = Campaign(user_id=_USER_ID, name=name, status=CampaignStatus.ACTIVE, channel="email")
    db.add(campaign)
    db.flush()
    return campaign


def _queued(
    db: Session,
    campaign: Campaign,
    prospect: ProspectDB,
    queue_type: str,
    status: str,
    skip_reason: str | None = None,
) -> EmailQueue:
    item = EmailQueue(
        user_id=_USER_ID,
        campaign_id=campaign.id,
        prospect_id=prospect.id,
        queue_type=queue_type,
        follow_up_index=1 if queue_type == "followup" else 0,
        scheduled_at=_IN_THREE_DAYS,
        status=status,
        skip_reason=skip_reason,
    )
    db.add(item)
    db.flush()
    return item


def _bounced_first_email(db: Session, campaign: Campaign, prospect: ProspectDB) -> EmailLog:
    email_log = EmailLog(
        user_id=_USER_ID,
        prospect_id=prospect.id,
        campaign_id=campaign.id,
        recipient_email=prospect.email,
        subject="le site",
        body_html="<p>le site</p>",
        provider="resend",
        status="bounced",
    )
    db.add(email_log)
    db.flush()
    return email_log


def test_a_bounced_first_email_is_re_sent_and_its_follow_up_is_held_back(db: Session) -> None:
    prospect = _prospect(db, "Bel Jaden", ["jaden@laposte.net", "jaden@gmail.com"])
    campaign = _campaign(db, "Vague 5 Martinique")
    first_email = _queued(db, campaign, prospect, "initial", "sent")
    follow_up = _queued(db, campaign, prospect, "followup", "pending")
    bounced = _bounced_first_email(db, campaign, prospect)
    db.commit()

    BounceFallbackService()._handle(db, bounced)

    assert prospect.email == "jaden@gmail.com"
    assert (follow_up.status, follow_up.skip_reason) == ("skipped", _HELD_BACK_REASON)
    assert first_email.status == "sent"
    re_sent = db.execute(
        select(EmailQueue).where(EmailQueue.queue_type == "initial", EmailQueue.status == "pending")
    ).scalar_one()
    assert (re_sent.campaign_id, re_sent.prospect_id) == (campaign.id, prospect.id)


def test_holding_back_leaves_other_campaigns_other_prospects_and_sent_follow_ups(db: Session) -> None:
    prospect = _prospect(db, "Bel Jaden", ["jaden@laposte.net"])
    neighbour = _prospect(db, "Green Garden", ["green@gmail.com"])
    campaign = _campaign(db, "Vague 5 Martinique")
    other_campaign = _campaign(db, "Dernier rappel")
    pending = _queued(db, campaign, prospect, "followup", "pending")
    already_sent = _queued(db, campaign, prospect, "followup", "sent")
    in_other_campaign = _queued(db, other_campaign, prospect, "followup", "pending")
    of_neighbour = _queued(db, campaign, neighbour, "followup", "pending")
    db.commit()

    held_back = CampaignQueueService(db).hold_back_follow_ups_of_bounced_first_email(campaign.id, prospect.id)

    assert held_back == 1
    assert (pending.status, pending.skip_reason) == ("skipped", _HELD_BACK_REASON)
    assert already_sent.status == "sent"
    assert in_other_campaign.status == "pending"
    assert of_neighbour.status == "pending"


def test_a_follow_up_held_back_after_a_bounce_does_not_stop_the_re_sent_email_from_arming_its_own(
    db: Session,
) -> None:
    prospect = _prospect(db, "Bel Jaden", ["jaden@gmail.com"])
    campaign = _campaign(db, "Vague 5 Martinique")
    _queued(db, campaign, prospect, "followup", "skipped", skip_reason=_HELD_BACK_REASON)
    db.commit()
    service = CampaignQueueService(db)

    assert service._has_follow_ups(campaign.id, prospect.id) is False

    _queued(db, campaign, prospect, "followup", "skipped", skip_reason="Annulé manuellement")
    db.commit()

    assert service._has_follow_ups(campaign.id, prospect.id) is True


def test_a_pending_follow_up_counts_as_an_existing_follow_up(db: Session) -> None:
    prospect = _prospect(db, "Bel Jaden", ["jaden@gmail.com"])
    campaign = _campaign(db, "Vague 5 Martinique")
    _queued(db, campaign, prospect, "followup", "pending")
    db.commit()

    assert CampaignQueueService(db)._has_follow_ups(campaign.id, prospect.id) is True
