/** Local shape of the campaign creation form. */
export type CreateCampaignForm = {
  name: string
  description: string
  templateIdA: number
  templateIdB: number
}

export type UiCreateCampaignDrawerEmits = {
  close: []
  back: []
}
