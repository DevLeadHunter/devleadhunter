import type { CampaignResultsTodo, CampaignResultsTodoAction } from '~/types/CampaignResults'

export type CampaignResultsTodoCardProps = {
  todos: CampaignResultsTodo[]
  emptyNote: string
}

export type CampaignResultsTodoCardEmits = {
  act: [action: CampaignResultsTodoAction]
}
