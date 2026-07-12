"""
Pydantic schemas for automatisations (the auto-chaining tunnel).
"""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from enums.acquisition import AcquisitionRunMode


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class SequenceFollowUpInput(BaseModel):
    """One follow-up step in an automatisation's campaign."""

    template_id: int
    delay_days: int = Field(5, ge=1, le=365)


class SequenceCreateRequest(BaseModel):
    """
    Create an automatisation.

    Selection (semi-auto): give ``prospect_ids``.
    Query (full-auto): give ``search_metiers`` + ``search_villes`` + ``target_days``.
    """

    name: str = Field(..., min_length=1, max_length=255)
    mode: AcquisitionRunMode = AcquisitionRunMode.SEMI_AUTO
    # Selection-based
    prospect_ids: List[int] = Field(default_factory=list)
    # Query-based (full-auto)
    search_metiers: List[str] = Field(default_factory=list)
    search_villes: List[str] = Field(default_factory=list)
    target_days: Optional[int] = Field(None, ge=1, le=90)
    only_without_website: bool = True
    # Steps
    auto_enrich: bool = True
    auto_generate: bool = True
    template_id: Optional[str] = None
    theme: Optional[dict] = None
    auto_campaign: bool = True
    email_template_id_a: Optional[int] = None
    email_template_id_b: Optional[int] = None
    send_delay_minutes: int = Field(20, ge=1, le=1440)
    follow_ups: List[SequenceFollowUpInput] = Field(default_factory=list)


class AssignTemplatesRequest(BaseModel):
    """Assign a demo template to some (or all pre-generation) items."""

    template_id: Optional[str] = None
    item_ids: Optional[List[int]] = None


class ItemIdsRequest(BaseModel):
    """A set of item ids (exclude / re-enrich)."""

    item_ids: List[int] = Field(..., min_length=1)


class RegenerateRequest(BaseModel):
    """Regenerate items, optionally with a new template."""

    item_ids: List[int] = Field(..., min_length=1)
    template_id: Optional[str] = None


class EmailPreviewRequest(BaseModel):
    """Render the real email for one item with a given template."""

    item_id: int
    template_id: int


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class EmailPreviewResponse(BaseModel):
    """A rendered email preview."""

    subject: str
    body_html: str


class UsedProspectsResponse(BaseModel):
    """Prospect ids already claimed by an automatisation (for the picker)."""

    prospect_ids: List[int]


class SequenceStats(BaseModel):
    """Derived, always-fresh counters for an automatisation."""

    total: int = 0
    by_step: Dict[str, int] = Field(default_factory=dict)
    won: int = 0
    emails_sent: int = 0
    credits_spent: int = 0


class SequenceItemResponse(BaseModel):
    """One prospect flowing through the automatisation."""

    id: int
    prospect_id: int
    prospect_name: Optional[str] = None
    prospect_city: Optional[str] = None
    prospect_email: Optional[str] = None
    step: str
    step_reason: Optional[str] = None
    template_id: Optional[str] = None
    demo_site_id: Optional[int] = None
    demo_slug: Optional[str] = None
    demo_url: Optional[str] = None
    demo_status: Optional[str] = None
    storyblok_editor_url: Optional[str] = None
    quality_score: Optional[int] = None
    quality_flags: Optional[List[str]] = None
    won: bool = False
    updated_at: Optional[datetime] = None


class SequenceResponse(BaseModel):
    """Summary of an automatisation (list view)."""

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
    search_metiers: Optional[List[str]] = None
    search_villes: Optional[List[str]] = None
    target_days: Optional[int] = None
    only_without_website: bool = True
    campaign_id: Optional[int] = None
    review_approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    stats: SequenceStats = Field(default_factory=SequenceStats)
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SequenceDetailResponse(SequenceResponse):
    """Full automatisation with its per-prospect items."""

    items: List[SequenceItemResponse] = Field(default_factory=list)


class SequenceListResponse(BaseModel):
    """Paginated automatisation list."""

    sequences: List[SequenceResponse]
    total: int
