import type { CampaignResultsTodo, CampaignResultsTodoAction } from '~/types/CampaignResults'

export type CampaignResultsTodoCardProps = {
  todos: CampaignResultsTodo[]
}

export type CampaignResultsTodoCardEmits = {
  act: [action: CampaignResultsTodoAction]
}
