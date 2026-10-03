import type { CampaignStatus } from '~/services/campaignService'
import type { CampaignFollowUp } from '~/types'
import type { CampaignBenchmark, CampaignResultsResponse } from '~/types/CampaignResults'

export type CampaignResultsTabProps = {
  campaignId: number
  campaignStatus: CampaignStatus
  followUps: CampaignFollowUp[]
  results: CampaignResultsResponse | null
  benchmarks: CampaignBenchmark[]
  isLoading: boolean
}

export type CampaignResultsTabEmits = {
  'open-prospect': [prospectId: number]
  'open-queue': []
  retry: []
}
