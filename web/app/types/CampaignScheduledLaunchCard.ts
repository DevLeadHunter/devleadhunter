export type CampaignScheduledLaunchCardProps = {
  scheduledLaunchAt: string | null
  scheduledLaunchError: string | null
  isPickerOpen: boolean
  isBusy: boolean
}

export type CampaignScheduledLaunchCardEmits = {
  schedule: [moment: Date]
  cancel: []
  'update:isPickerOpen': [isPickerOpen: boolean]
}
