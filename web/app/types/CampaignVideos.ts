/** A demo site of the campaign, to link from where its video stands. */
export type CampaignVideoSite = {
  demo_site_id: number
  business_name: string
}

/** The campaign's demo sites sorted by where their video stands, and whether the owner's PC is on to build them. */
export type CampaignVideosResponse = {
  uses_video: boolean
  is_desktop_app_online: boolean
  ready: CampaignVideoSite[]
  ready_with_older_clip: CampaignVideoSite[]
  waiting_for_desktop: CampaignVideoSite[]
  waiting_for_storyblok_space: CampaignVideoSite[]
  building: CampaignVideoSite[]
  failed: CampaignVideoSite[]
  not_requested: CampaignVideoSite[]
}

/** A demo site whose video was not asked from the PC, and why. */
export type CampaignVideoSkippedSite = {
  demo_site_id: number
  business_name: string
  reason: string
}

/** How many videos of the campaign were asked from the owner's PC, and the sites left aside. */
export type CampaignVideoRequestsResponse = {
  requested_count: number
  skipped: CampaignVideoSkippedSite[]
}
