export type CampaignVideoSite = {
  demo_site_id: number
  business_name: string
}

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

export type CampaignVideoSkippedSite = {
  demo_site_id: number
  business_name: string
  reason: string
}

export type CampaignVideoRequestsResponse = {
  requested_count: number
  skipped: CampaignVideoSkippedSite[]
}
