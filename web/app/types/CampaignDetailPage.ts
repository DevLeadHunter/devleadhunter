import type { CampaignQueueItem } from '~/services/campaignService'

/** Lightweight template shape used by the selects. */
export type TemplateOption = {
  id: number
  name: string
  subject: string
}

export type CampaignQueueRow = CampaignQueueItem & {
  prospectLocalTimeLabel: string | null
}
