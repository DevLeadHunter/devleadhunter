"""
The prospection videos of a campaign's demo sites: where each one stands, and asking the owner's PC for the missing ones.

A campaign about to go out after a new presenter clip needs its videos rebuilt first; the campaign page asks for them
from any device, and the desktop app builds them in the background.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from enums.demo_video_status import DemoVideoStatus
from models.campaign import Campaign
from models.demo_site import DemoSite
from schemas.campaign_videos import (
    CampaignVideoRequestsResponse,
    CampaignVideoSite,
    CampaignVideoSkippedSite,
    CampaignVideosResponse,
)
from services.campaign_queue_service import CampaignQueueService
from services.demo_video_service import demo_video_service, has_ready_video
from services.prospect_search.desktop_app_presence import desktop_app_presence
from services.prospection_video_desktop_relay import demo_video_desktop_relay

ALREADY_REQUESTED_REASON = "Déjà demandée à votre PC."


class CampaignVideosService:
    """Sorts a campaign's demo sites by where their video stands, and asks the owner's PC for their videos."""

    @classmethod
    def summarize(cls, db: Session, campaign: Campaign) -> CampaignVideosResponse:
        """
        Sort the campaign's demo sites by where their video stands.

        Args:
            db: Active database session.
            campaign: The user's campaign.

        Returns:
            The sites of each state, whether the campaign's messages show the video, and whether the PC is on.
        """
        clip_in_use_since = demo_video_service.clip_in_use_since(db, campaign.user_id)
        summary = CampaignVideosResponse(
            uses_video=CampaignQueueService(db).uses_site_video(campaign),
            is_desktop_app_online=desktop_app_presence.is_online(campaign.user_id),
        )
        for site in cls._active_sites(db, campaign):
            listed_site = CampaignVideoSite(demo_site_id=site.id, business_name=site.business_name)
            if demo_video_service.is_desktop_build_started(site):
                summary.building.append(listed_site)
            elif demo_video_service.is_waiting_for_storyblok_space(site):
                summary.waiting_for_storyblok_space.append(listed_site)
            elif site.video_desktop_requested_at is not None:
                summary.waiting_for_desktop.append(listed_site)
            elif demo_video_service.is_made_with_older_clip(site, clip_in_use_since):
                summary.ready_with_older_clip.append(listed_site)
            elif has_ready_video(site):
                summary.ready.append(listed_site)
            elif site.video_status == DemoVideoStatus.FAILED.value:
                summary.failed.append(listed_site)
            else:
                summary.not_requested.append(listed_site)
        return summary

    @classmethod
    def request_videos(cls, db: Session, campaign: Campaign, *, redo: bool) -> CampaignVideoRequestsResponse:
        """
        Ask the owner's PC for the videos the campaign's demo sites lack, or for all of them.

        A site whose video is already asked keeps its place in the PC's queue; a site the PC cannot film is left aside
        with the reason the relay gives.

        Args:
            db: Active database session.
            campaign: The user's campaign.
            redo: Ask again for the videos already made with the presenter clip in use.

        Returns:
            How many videos were asked, and the sites left aside with their reason.
        """
        clip_in_use_since = demo_video_service.clip_in_use_since(db, campaign.user_id)
        outcome = CampaignVideoRequestsResponse()
        for site in cls._active_sites(db, campaign):
            if site.video_desktop_requested_at is not None:
                outcome.skipped.append(cls._skipped(site, ALREADY_REQUESTED_REASON))
                continue
            has_video_with_clip_in_use = has_ready_video(site) and not demo_video_service.is_made_with_older_clip(
                site, clip_in_use_since
            )
            if has_video_with_clip_in_use and not redo:
                continue
            try:
                demo_video_desktop_relay.request(db, site, campaign.user_id)
            except ValueError as exc:
                outcome.skipped.append(cls._skipped(site, str(exc)))
                continue
            outcome.requested_count += 1
        return outcome

    @staticmethod
    def _active_sites(db: Session, campaign: Campaign) -> list[DemoSite]:
        """
        The active demo site of each of the campaign's prospects, in the campaign's sending order.

        Args:
            db: Active database session.
            campaign: The user's campaign.

        Returns:
            The sites; a prospect without an active demo site has none.
        """
        prospect_ids = [prospect.id for prospect in campaign.prospects]
        sites_by_prospect = CampaignQueueService(db).active_demos_by_prospect(prospect_ids, campaign.user_id)
        return [sites_by_prospect[prospect_id] for prospect_id in prospect_ids if prospect_id in sites_by_prospect]

    @staticmethod
    def _skipped(site: DemoSite, reason: str) -> CampaignVideoSkippedSite:
        """
        A site whose video was not asked.

        Args:
            site: The demo site.
            reason: Why it was left aside.

        Returns:
            The site and its reason.
        """
        return CampaignVideoSkippedSite(demo_site_id=site.id, business_name=site.business_name, reason=reason)
