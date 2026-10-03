import type { SelectFieldOption } from '~/types/SelectField'

export type UiCampaignReplyDrawerProps = {
  open: boolean
  showBack: boolean
  campaignId: number | null
  prospects: SelectFieldOption<number>[]
}

export type UiCampaignReplyDrawerEmits = {
  close: []
  back: []
  saved: []
}
