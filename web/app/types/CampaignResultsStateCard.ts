import type { CampaignChannelWords } from '~/types/CampaignChannelWords'
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
  words: CampaignChannelWords
}

export type CampaignResultsStateCardEmits = {
  'select-prospect': [prospectId: number]
  'select-state': [state: CampaignResultsProspectState]
  'show-prospects': []
  'open-queue': []
}
