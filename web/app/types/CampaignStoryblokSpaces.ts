export type CampaignStoryblokSpaceSite = {
  demo_site_id: number
  business_name: string
}

export type CampaignStoryblokKeptSpace = CampaignStoryblokSpaceSite & {
  reason: string
}

export type CampaignStoryblokSpacesResponse = {
  releasable: CampaignStoryblokSpaceSite[]
  kept: CampaignStoryblokKeptSpace[]
  account_space_count: number | null
  account_space_limit: number
}
