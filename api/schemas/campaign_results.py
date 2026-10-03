"""
Contracts of a campaign's results: what its mails produced, prospect by prospect.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CampaignResultsProspectState = Literal[
    "sold", "interested", "refused", "replied", "visited", "silent", "pending", "not_sent"
]
CampaignResultsSendStatus = Literal["sent", "planned", "skipped", "failed"]
CampaignResultsReplyVerdict = Literal["interested", "refused", "other"]
CampaignResultsReplyChannel = Literal["email", "banner", "manual"]


class CampaignResultsSend(BaseModel):
    """One mail of a prospect's sequence: the first mail (step 0) or a follow-up (step 1 and up)."""

    step: int
    status: CampaignResultsSendStatus
    at: datetime
    is_bounced: bool = False


class CampaignResultsVisit(BaseModel):
    """One human visit of a prospect's demo, with the time the page stayed in front of them."""

    started_at: datetime
    active_seconds: int
    device_type: str | None = None


class CampaignResultsReply(BaseModel):
    """A prospect's reply, whichever way it came: a captured mail, the demo banner, or added by hand."""

    id: str
    prospect_id: int
    received_at: datetime
    verdict: CampaignResultsReplyVerdict
    channel: CampaignResultsReplyChannel
    answered_step: int
    excerpt: str
    is_handled: bool


class CampaignResultsProspect(BaseModel):
    """A prospect of the campaign with everything that happened to them since the first mail."""

    id: int
    name: str
    category: str
    city: str | None = None
    state: CampaignResultsProspectState
    is_email_undeliverable: bool = False
    sends: list[CampaignResultsSend]
    visits: list[CampaignResultsVisit]


class CampaignResultsTotals(BaseModel):
    """Prospect counts at each stage, plus the mail volumes behind them."""

    prospects: int
    contacted: int
    visited: int
    replied: int
    interested: int
    refused: int
    sales: int
    revenue_cents: int
    currency: str | None = None
    first_mails_sent: int
    follow_ups_sent: int
    bounced: int
    failed: int
    planned_first_mails: int
    planned_follow_ups: int


class CampaignResultsNextSend(BaseModel):
    """The next planned mail of the campaign and the prospect it goes to."""

    at: datetime
    prospect_name: str


class CampaignResultsDemoSites(BaseModel):
    """Demo sites of the campaign still online, and when the first and the last of them expire."""

    online: int
    first_expiry_at: datetime | None = None
    last_expiry_at: datetime | None = None


class CampaignResultsResponse(BaseModel):
    """Payload of a campaign's « Résultats » tab."""

    campaign_id: int
    generated_at: datetime
    is_visit_tracking_available: bool
    totals: CampaignResultsTotals
    next_send: CampaignResultsNextSend | None = None
    last_planned_send_at: datetime | None = None
    demo_sites: CampaignResultsDemoSites
    prospects: list[CampaignResultsProspect]
    replies: list[CampaignResultsReply]


class CampaignBenchmark(BaseModel):
    """Stage counts of another campaign, to compare a campaign's rates against."""

    campaign_id: int
    name: str
    status: str
    started_at: datetime | None = None
    contacted: int
    visited: int
    replied: int
    interested: int


class CampaignBenchmarksResponse(BaseModel):
    """The user's email campaigns that have sent at least one first mail, most recent first."""

    campaigns: list[CampaignBenchmark]


class CampaignManualReplyCreate(BaseModel):
    """A reply that reached the user outside the app (their own inbox, a call), added by hand."""

    prospect_id: int
    verdict: CampaignResultsReplyVerdict
    received_at: datetime | None = None
    message: str = Field(default="", max_length=5000)
