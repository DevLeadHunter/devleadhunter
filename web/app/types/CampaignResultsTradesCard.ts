import type { CampaignResultsTradeGroup } from '~/types/CampaignResults'

export type CampaignResultsTradesCardProps = {
  groups: CampaignResultsTradeGroup[]
  note: string
}

export type CampaignResultsTradesCardEmits = {
  'select-prospect': [prospectId: number]
}
