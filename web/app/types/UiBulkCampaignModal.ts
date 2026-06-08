/**
 * Props for the UiBulkCampaignModal component.
 */
export interface UiBulkCampaignModalProps {
  /** Whether the modal is visible. */
  open: boolean
  /** IDs of the prospects to add to a campaign. */
  prospectIds: number[]
}

/**
 * Payload emitted once prospects have been added to a campaign.
 */
export interface UiBulkCampaignModalAdded {
  /** Name of the campaign the prospects were added to. */
  campaignName: string
  /** Number of prospects submitted. */
  count: number
}
