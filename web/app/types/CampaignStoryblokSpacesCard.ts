import type { CampaignStoryblokKeptSpace, CampaignStoryblokSpaceSite } from '~/types/CampaignStoryblokSpaces'

export type CampaignStoryblokSpacesCardProps = {
  campaignId: number
}

export type CampaignStoryblokKeptGroup = {
  reason: string
  sites: CampaignStoryblokKeptSpace[]
}

export type CampaignStoryblokReleaseFailure = {
  site: CampaignStoryblokSpaceSite
  reason: string
}

export type CampaignStoryblokReleaseOutcome = {
  releasedCount: number
  failures: CampaignStoryblokReleaseFailure[]
}
