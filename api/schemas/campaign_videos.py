"""Schemas of the prospection videos of a campaign's demo sites (``/campaigns/{id}/videos``)."""

from pydantic import BaseModel, Field


class CampaignVideoSite(BaseModel):
    """A demo site of the campaign, to link from where its video stands."""

    demo_site_id: int
    business_name: str


class CampaignVideosResponse(BaseModel):
    """The campaign's demo sites sorted by where their video stands, and whether the owner's PC is on to build them."""

    uses_video: bool
    is_desktop_app_online: bool
    ready: list[CampaignVideoSite] = Field(default_factory=list)
    ready_with_older_clip: list[CampaignVideoSite] = Field(default_factory=list)
    waiting_for_desktop: list[CampaignVideoSite] = Field(default_factory=list)
    waiting_for_storyblok_space: list[CampaignVideoSite] = Field(default_factory=list)
    building: list[CampaignVideoSite] = Field(default_factory=list)
    failed: list[CampaignVideoSite] = Field(default_factory=list)
    not_requested: list[CampaignVideoSite] = Field(default_factory=list)


class CampaignVideoRequestsCreate(BaseModel):
    """Which videos of the campaign to ask from the owner's PC."""

    redo: bool = False


class CampaignVideoSkippedSite(BaseModel):
    """A demo site whose video was not asked, and why."""

    demo_site_id: int
    business_name: str
    reason: str


class CampaignVideoRequestsResponse(BaseModel):
    """How many videos of the campaign were asked from the owner's PC, and the sites left aside."""

    requested_count: int = 0
    skipped: list[CampaignVideoSkippedSite] = Field(default_factory=list)
