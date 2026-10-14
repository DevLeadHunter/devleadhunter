"""An email whose only door is the site video never leaves without that video.

The « Rappel court - vidéo » relance writes the demo's closing date but links nothing but the video
thumbnail: without a ready video it would reach the prospect with no link at all. It is held back
with its reason, while a template that also carries ``{lien_demo}`` still leaves with the demo link.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from models.campaign import Campaign, CampaignStatus
from models.demo_site import DemoSite
from models.email_queue import EmailQueue
from models.email_template import EmailTemplate
from models.prospect_db import ProspectDB
from models.user import User
from services.campaign_queue_service import CampaignQueueService

_VIDEO_RELANCE_BODY = "<p>{salutation},</p><p>Le site de {entreprise}, en 30 secondes :</p>{vignette_video}<p>Je le retire le {date_expiration}.</p>"
_VIDEO_AND_DEMO_BODY = "<p>{salutation},</p>{vignette_video}<p>Votre site : {lien_demo}</p>"


def _claimed_relance(db: Session, *, body_html: str) -> EmailQueue:
    """A J+3 relance of an active email campaign, just claimed by the worker, for a prospect whose site has no video."""
    sender = User(name="Jean Dupont", email="jean@example.com", hashed_password="x", company_name="Dibodev")
    db.add(sender)
    db.flush()
    prospect = ProspectDB(
        user_id=sender.id,
        name="Jardins Martin",
        category="paysagiste",
        source="google_maps",
        email="contact@jardins-martin.example",
        country="FR",
    )
    db.add(prospect)
    db.flush()
    db.add(
        DemoSite(
            user_id=sender.id,
            prospect_id=prospect.id,
            slug="jardins-martin",
            business_name="Jardins Martin",
            demo_url="https://demo.example.com/jardins-martin",
            status="active",
            expires_at=datetime.now(UTC) + timedelta(days=18),
        )
    )
    template = EmailTemplate(user_id=sender.id, name="Rappel court - vidéo", subject="votre site", body_html=body_html)
    db.add(template)
    db.flush()
    campaign = Campaign(
        user_id=sender.id,
        name="Vague 4",
        status=CampaignStatus.ACTIVE,
        channel="email",
        template_id=template.id,
        include_video=True,
    )
    db.add(campaign)
    db.flush()
    item = EmailQueue(
        user_id=sender.id,
        campaign_id=campaign.id,
        prospect_id=prospect.id,
        template_id=template.id,
        queue_type="followup",
        follow_up_index=1,
        scheduled_at=datetime.now(UTC).replace(tzinfo=None),
        status="sending",
    )
    db.add(item)
    db.commit()
    return item


def test_a_video_relance_is_held_back_while_the_video_is_missing(
    db: Session, resend_payloads: list[dict[str, Any]]
) -> None:
    item = _claimed_relance(db, body_html=_VIDEO_RELANCE_BODY)

    asyncio.run(CampaignQueueService(db)._dispatch(item))

    assert (item.status, item.skip_reason) == ("skipped", "Pas de vidéo prête")
    assert resend_payloads == []


def test_a_relance_that_also_links_the_demo_leaves_with_the_demo_link(
    db: Session, resend_payloads: list[dict[str, Any]]
) -> None:
    item = _claimed_relance(db, body_html=_VIDEO_AND_DEMO_BODY)

    asyncio.run(CampaignQueueService(db)._dispatch(item))

    assert item.status == "sent"
    assert "jardins-martin" in resend_payloads[0]["html_body"]
