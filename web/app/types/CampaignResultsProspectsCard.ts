import type { CampaignResultsDay, CampaignResultsRow, CampaignResultsSortKey } from '~/types/CampaignResults'

export type CampaignResultsProspectsCardProps = {
  rows: CampaignResultsRow[]
  days: CampaignResultsDay[]
  periodLabel: string
  isVisitTrackingAvailable: boolean
}

export type CampaignResultsProspectsCardEmits = {
  'open-prospect': [prospectId: number]
}

export type CampaignResultsProspectsCardExposed = {
  reveal: (prospectId: number | null) => Promise<void>
}

export type CampaignResultsSortableColumn = {
  key: CampaignResultsSortKey
  label: string
  hiddenBelow: '4xl' | '5xl' | null
}
