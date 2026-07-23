export type UiBulkCampaignModalProps = {
  open: boolean
  prospectIds: number[]
}

/**
 * Payload emitted once prospects have been added to a campaign.
 */
export type UiBulkCampaignModalAdded = {
  campaignName: string
  count: number
}
