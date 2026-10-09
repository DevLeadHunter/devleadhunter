import type { CampaignResponse } from '~/services/campaignService'
import type { CampaignVideoSite } from '~/types/CampaignVideos'

export type CampaignVideosCardProps = {
  campaign: CampaignResponse
}

export type CampaignVideoStateKey =
  | 'ready'
  | 'ready_with_older_clip'
  | 'building'
  | 'waiting_for_desktop'
  | 'waiting_for_storyblok_space'
  | 'failed'
  | 'not_requested'

export type CampaignVideoStateWording = {
  key: CampaignVideoStateKey
  icon: string
  iconClass: string
  singularLabel: string
  pluralLabel: string
}

export type CampaignVideoStateLine = {
  key: CampaignVideoStateKey
  icon: string
  iconClass: string
  label: string
  sites: CampaignVideoSite[]
}
