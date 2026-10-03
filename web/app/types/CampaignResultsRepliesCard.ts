import type { CampaignChannelWords } from '~/types/CampaignChannelWords'
import type { CampaignResultsReply, CampaignResultsRow } from '~/types/CampaignResults'

export type CampaignResultsRepliesCardProps = {
  replies: CampaignResultsReply[]
  rows: CampaignResultsRow[]
  words: CampaignChannelWords
}

export type CampaignResultsRepliesCardEmits = {
  'open-prospect': [prospectId: number]
  'add-reply': []
}

export type CampaignResultsReplyLine = {
  reply: CampaignResultsReply
  prospectName: string
  receivedLabel: string
  originLabel: string
}
