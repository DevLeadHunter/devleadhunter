"""
Pydantic schemas for acquisition sequences (the auto-chaining tunnel).
"""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from enums.acquisition import AcquisitionRunMode


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class SequenceFollowUpInput(BaseModel):
    """One follow-up step in a sequence's campaign."""

    template_id: int
    delay_days: int = Field(5, ge=1, le=365)


class SequenceCreateRequest(BaseModel):
    """Create a sequence from a batch of already-found prospects (Phase 1)."""

    name: str = Field(..., min_length=1, max_length=255)
    prospect_ids: List[int] = Field(..., min_length=1)
    mode: AcquisitionRunMode = AcquisitionRunMode.SEMI_AUTO
    auto_enrich: bool = True
    auto_generate: bool = True
    # Demo-site template id (e.g. "artisan-edito"); None → default template.
    template_id: Optional[str] = None
    auto_campaign: bool = True
    email_template_id_a: Optional[int] = None
    email_template_id_b: Optional[int] = None
    send_delay_minutes: int = Field(20, ge=1, le=1440)
    follow_ups: List[SequenceFollowUpInput] = Field(default_factory=list)
    max_credits: Optional[int] = Field(None, ge=0)
    daily_email_cap: Optional[int] = Field(None, ge=1)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class SequenceStats(BaseModel):
    """Derived, always-fresh counters for a sequence."""

    total: int = 0
    by_step: Dict[str, int] = Field(default_factory=dict)
    won: int = 0
    emails_sent: int = 0
    credits_spent: int = 0


class SequenceItemResponse(BaseModel):
    """One prospect flowing through the sequence."""

    id: int
    prospect_id: int
    prospect_name: Optional[str] = None
    prospect_city: Optional[str] = None
    prospect_email: Optional[str] = None
    step: str
    step_reason: Optional[str] = None
    demo_site_id: Optional[int] = None
    demo_slug: Optional[str] = None
    demo_url: Optional[str] = None
    demo_status: Optional[str] = None
    won: bool = False
    updated_at: Optional[datetime] = None


class SequenceResponse(BaseModel):
    """Summary of a sequence (list view)."""

    id: int
    name: str
    status: str
    mode: str
    auto_enrich: bool
    auto_generate: bool
    template_id: Optional[str] = None
    auto_campaign: bool
    email_template_id_a: Optional[int] = None
    email_template_id_b: Optional[int] = None
    send_delay_minutes: int
    campaign_id: Optional[int] = None
    max_credits: Optional[int] = None
    daily_email_cap: Optional[int] = None
    review_approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    stats: SequenceStats = Field(default_factory=SequenceStats)

    model_config = ConfigDict(from_attributes=True)


class SequenceDetailResponse(SequenceResponse):
    """Full sequence with its per-prospect items."""

    items: List[SequenceItemResponse] = Field(default_factory=list)


class SequenceListResponse(BaseModel):
    """Paginated sequence list."""

    sequences: List[SequenceResponse]
    total: int
