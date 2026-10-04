import type { CampaignQueueItem } from '~/services/campaignService'

/** Lightweight template shape used by the selects. */
export type TemplateOption = {
  id: number
  name: string
  subject: string
  is_active: boolean
}

export type CampaignQueueRow = CampaignQueueItem & {
  prospectLocalTimeLabel: string | null
}

export type CampaignDetailTab = {
  key: string
  label: string
}

export type CampaignSmsFollowUpForm = {
  isEnabled: boolean
  delayDays: number
  templateKey: string
}
