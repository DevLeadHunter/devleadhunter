"""
The Storyblok spaces of a campaign's demo sites: which can be released together, and which stay with the reason.

A space only serves to film a demo's video and to sell it. Once the demo has gone out and its video is made, releasing it
makes room without touching the demo; but a prospect who looked at their demo, answered it, or was invited into the
space keeps theirs, whichever campaign they did it in.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.campaign import Campaign, campaign_prospects
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

ENGAGED_STATES_FROM_WEAKEST: tuple[str, ...] = ("visited", "replied", "interested", "sold")
KEPT_REASON_BY_STATE_IN_ANOTHER_CAMPAIGN: dict[str, str] = {
    "visited": "A regardé sa démo dans une autre campagne.",
    "replied": "A répondu dans une autre campagne.",
    "interested": "S'est dit intéressé dans une autre campagne.",
    "sold": "A acheté dans une autre campagne.",
}


class CampaignStoryblokSpacesService:
    """Sorts a campaign's Storyblok spaces between those a release can take and those that stay."""

    @classmethod
    async def summarize(cls, db: Session, campaign: Campaign) -> CampaignStoryblokSpacesResponse:
        """
        Split the campaign's spaces between the releasable ones and the ones that stay.

        A space is released only for a prospect who stayed silent (no human visit, no answer) or refused, in this
        campaign and in every other one they are in, once the demo's own conditions hold (sent, video made, nobody
        invited); when the visits cannot be read, none is.

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
        reasons_by_site_id = {
            site.id: cls._reason_to_keep(site, states_by_prospect.get(site.prospect_id), is_visit_tracking_available)
            for site in sites
        }
        prospect_ids_to_release = [site.prospect_id for site in sites if reasons_by_site_id[site.id] is None]
        reasons_from_other_campaigns = await cls._reasons_from_other_campaigns(db, campaign, prospect_ids_to_release)
        for site in sites:
            reason = reasons_by_site_id[site.id]
            if reason is None:
                reason = reasons_from_other_campaigns.get(site.prospect_id)
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

    @classmethod
    async def _reasons_from_other_campaigns(
        cls, db: Session, campaign: Campaign, prospect_ids: list[int]
    ) -> dict[int, str]:
        """
        Why a prospect's space stays because of another campaign they are in.

        A campaign's results only count the visits and answers of its own window, so a prospect who looked at their
        demo during an earlier campaign reads as silent in a later one: their other campaigns are read too.

        Args:
            db: Active database session.
            campaign: The campaign being summarized, left out.
            prospect_ids: The prospects that would otherwise be released.

        Returns:
            ``prospect_id`` to the reason, for the prospects who engaged in another campaign or whose results there
            could not be read.
        """
        if not prospect_ids:
            return {}
        rows = db.execute(
            select(Campaign.id, Campaign.user_id, campaign_prospects.c.prospect_id)
            .join(campaign_prospects, campaign_prospects.c.campaign_id == Campaign.id)
            .where(campaign_prospects.c.prospect_id.in_(prospect_ids), Campaign.id != campaign.id)
            .order_by(Campaign.id)
        ).all()
        prospect_ids_by_campaign: dict[tuple[int, int], set[int]] = {}
        for other_campaign_id, other_user_id, prospect_id in rows:
            prospect_ids_by_campaign.setdefault((other_campaign_id, other_user_id), set()).add(prospect_id)

        unreadable_prospect_ids: set[int] = set()
        strongest_state_by_prospect: dict[int, str] = {}
        for (other_campaign_id, other_user_id), other_prospect_ids in prospect_ids_by_campaign.items():
            results = await campaign_results_service.build(db, other_user_id, other_campaign_id)
            if results is None or not results.is_visit_tracking_available:
                unreadable_prospect_ids |= other_prospect_ids
                continue
            for prospect in results.prospects:
                if prospect.id not in other_prospect_ids or prospect.state not in ENGAGED_STATES_FROM_WEAKEST:
                    continue
                strongest_state = strongest_state_by_prospect.get(prospect.id)
                if strongest_state is None or cls._is_stronger(prospect.state, strongest_state):
                    strongest_state_by_prospect[prospect.id] = prospect.state

        reasons = dict.fromkeys(unreadable_prospect_ids, TRACKING_UNAVAILABLE_REASON)
        for prospect_id, state in strongest_state_by_prospect.items():
            reasons[prospect_id] = KEPT_REASON_BY_STATE_IN_ANOTHER_CAMPAIGN[state]
        return reasons

    @staticmethod
    def _is_stronger(state: str, other_state: str) -> bool:
        """Whether ``state`` is further along the way to a sale than ``other_state``, both being engaged states."""
        return ENGAGED_STATES_FROM_WEAKEST.index(state) > ENGAGED_STATES_FROM_WEAKEST.index(other_state)

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
