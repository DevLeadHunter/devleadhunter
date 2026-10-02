import type { CampaignQueueItem } from '~/services/campaignService'

/** Lightweight template shape used by the selects. */
export type TemplateOption = {
  id: number
  name: string
  subject: string
}

/** A queue row as the « File » tab renders it: the item plus the prospect's local hour when it differs from the viewer's. */
export type CampaignQueueRow = CampaignQueueItem & {
  prospectLocalTimeLabel: string | null
}
