import type { CampaignResultsDay, CampaignResultsReplyVerdict, CampaignResultsRow } from '~/types/CampaignResults'

export type CampaignResultsJourneyProps = {
  row: CampaignResultsRow
  days: CampaignResultsDay[]
}

export type CampaignResultsJourneyMailKind = 'firstMail' | 'followUp' | 'planned' | 'cancelled' | 'failed'

export type CampaignResultsJourneyMail = {
  key: string
  kind: CampaignResultsJourneyMailKind
  x: number
}

export type CampaignResultsJourneyVisitDot = {
  key: string
  x: number
  radius: number
}

export type CampaignResultsJourneyReplyMark = {
  key: string
  x: number
  verdict: CampaignResultsReplyVerdict
}

export type CampaignResultsJourneyEvent = {
  key: string
  at: Date
  label: string
}
