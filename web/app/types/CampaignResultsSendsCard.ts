import type { CampaignChannelWords } from '~/types/CampaignChannelWords'
import type { CampaignResultsStepSummary } from '~/types/CampaignResults'

export type CampaignResultsSendsCardProps = {
  steps: CampaignResultsStepSummary[]
  prospectNames: Record<number, string>
  prospectCount: number
  note: string
  isVisitTrackingAvailable: boolean
  words: CampaignChannelWords
}
