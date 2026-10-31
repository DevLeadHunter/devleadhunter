"""Schemas of the Storyblok spaces of a campaign's demo sites (``/campaigns/{id}/storyblok-spaces``)."""

from pydantic import BaseModel, Field


class CampaignStoryblokSpaceSite(BaseModel):
    """A demo site of the campaign that holds a Storyblok space, to link from the list it belongs to."""

    demo_site_id: int
    business_name: str


class CampaignStoryblokKeptSpace(CampaignStoryblokSpaceSite):
    """A space that stays, with the reason the dashboard shows."""

    reason: str


class CampaignStoryblokSpacesResponse(BaseModel):
    """The campaign's spaces split between those a release can take and those that stay, and what the account holds."""

    releasable: list[CampaignStoryblokSpaceSite] = Field(default_factory=list)
    kept: list[CampaignStoryblokKeptSpace] = Field(default_factory=list)
    account_space_count: int | None = None
    account_space_limit: int
