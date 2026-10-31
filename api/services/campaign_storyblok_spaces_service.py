"""
The Storyblok spaces of a campaign's demo sites: which can be released together, and which stay with the reason.

A space only serves to film a demo's video and to sell it. Once the demo has gone out and its video is made, releasing it
makes room without touching the demo; but a prospect who looked at their demo, answered it, or was invited into the
space keeps theirs.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.campaign import Campaign
from models.demo_site import DemoSite
from schemas.campaign_results import CampaignResultsResponse
from schemas.campaign_storyblok_spaces import (
    CampaignStoryblokKeptSpace,
    CampaignStoryblokSpaceSite,
    CampaignStoryblokSpacesResponse,
)
from services.campaign_queue_service import CampaignQueueService
from services.campaign_results_service import campaign_results_service
from services.demo_site_service import demo_site_service
from services.storyblok_service import storyblok_service

STORYBLOK_SPACE_LIMIT: int = 250

TRACKING_UNAVAILABLE_REASON: str = "Le suivi des visites est indisponible : on ne sait pas s'il a regardé sa démo."
UNKNOWN_PROSPECT_REASON: str = "On ne sait pas où en est ce prospect."

RELEASABLE_PROSPECT_STATES: frozenset[str] = frozenset({"silent", "refused"})
KEPT_REASON_BY_PROSPECT_STATE: dict[str, str] = {
    "visited": "A regardé sa démo.",
    "replied": "A répondu.",
    "interested": "S'est dit intéressé.",
    "sold": "A acheté.",
    "pending": "Pas encore contacté.",
    "not_sent": "Pas encore contacté.",
}


class CampaignStoryblokSpacesService:
    """Sorts a campaign's Storyblok spaces between those a release can take and those that stay."""

    @classmethod
    async def summarize(cls, db: Session, campaign: Campaign) -> CampaignStoryblokSpacesResponse:
        """
        Split the campaign's spaces between the releasable ones and the ones that stay.

        A space is released only for a prospect who stayed silent (no human visit, no answer) or refused, once the
        demo's own conditions hold (sent, video made, nobody invited); when the visits cannot be read, none is.

        Args:
            db: Active database session.
            campaign: The user's campaign.

        Returns:
            The releasable and the kept sites, and how many spaces the account holds against its cap.
        """
        summary = CampaignStoryblokSpacesResponse(
            account_space_count=await storyblok_service.count_spaces(),
            account_space_limit=STORYBLOK_SPACE_LIMIT,
        )
        sites = cls._sites_with_a_space(db, campaign)
        if not sites:
            return summary

        results = await campaign_results_service.build(db, campaign.user_id, campaign.id)
        states_by_prospect = cls._states_by_prospect(results)
        is_visit_tracking_available = results is not None and results.is_visit_tracking_available
        for site in sites:
            reason = cls._reason_to_keep(site, states_by_prospect.get(site.prospect_id), is_visit_tracking_available)
            if reason is None:
                summary.releasable.append(
                    CampaignStoryblokSpaceSite(demo_site_id=site.id, business_name=site.business_name)
                )
            else:
                summary.kept.append(
                    CampaignStoryblokKeptSpace(demo_site_id=site.id, business_name=site.business_name, reason=reason)
                )
        return summary

    @staticmethod
    def _sites_with_a_space(db: Session, campaign: Campaign) -> list[DemoSite]:
        """
        The active demo site of each of the campaign's prospects that holds a Storyblok space, in sending order.

        Args:
            db: Active database session.
            campaign: The user's campaign.

        Returns:
            The sites; a prospect without an active demo site or without its space has none.
        """
        prospect_ids = [prospect.id for prospect in campaign.prospects]
        sites_by_prospect = CampaignQueueService(db).active_demos_by_prospect(prospect_ids, campaign.user_id)
        return [
            sites_by_prospect[prospect_id]
            for prospect_id in prospect_ids
            if prospect_id in sites_by_prospect and sites_by_prospect[prospect_id].storyblok_space_id
        ]

    @staticmethod
    def _states_by_prospect(results: CampaignResultsResponse | None) -> dict[int, str]:
        """
        Where each prospect of the campaign stands, as the campaign's results read it.

        Args:
            results: The campaign's results, or None when they could not be built.

        Returns:
            ``prospect_id`` to the furthest stage the prospect reached.
        """
        if results is None:
            return {}
        return {prospect.id: prospect.state for prospect in results.prospects}

    @staticmethod
    def _reason_to_keep(site: DemoSite, prospect_state: str | None, is_visit_tracking_available: bool) -> str | None:
        """
        Why the site's space stays, in the words the dashboard shows.

        Args:
            site: The demo site holding the space.
            prospect_state: The furthest stage its prospect reached, when known.
            is_visit_tracking_available: Whether the human visits of the demos could be read.

        Returns:
            The reason, or None when the space can be released.
        """
        site_blocker = demo_site_service.storyblok_release_blocker(site)
        if site_blocker:
            return site_blocker
        if not is_visit_tracking_available:
            return TRACKING_UNAVAILABLE_REASON
        if prospect_state in RELEASABLE_PROSPECT_STATES:
            return None
        return KEPT_REASON_BY_PROSPECT_STATE.get(prospect_state or "", UNKNOWN_PROSPECT_REASON)
