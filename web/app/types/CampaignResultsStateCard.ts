import type {
  CampaignResultsProspectState,
  CampaignResultsStateFact,
  CampaignResultsStateGroup,
} from '~/types/CampaignResults'

export type CampaignResultsStateCardProps = {
  groups: CampaignResultsStateGroup[]
  facts: CampaignResultsStateFact[]
  prospectCount: number
  isSending: boolean
  isAloneOnRow: boolean
}

export type CampaignResultsStateCardEmits = {
  'select-prospect': [prospectId: number]
  'select-state': [state: CampaignResultsProspectState]
  'show-prospects': []
  'open-queue': []
}
