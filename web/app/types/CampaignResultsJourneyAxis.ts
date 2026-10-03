import type { CampaignResultsDay } from '~/types/CampaignResults'

export type CampaignResultsJourneyAxisProps = {
  days: CampaignResultsDay[]
}

export type CampaignResultsJourneyAxisLabel = {
  key: string
  x: number
  text: string
  isToday: boolean
  isWeekend: boolean
}
