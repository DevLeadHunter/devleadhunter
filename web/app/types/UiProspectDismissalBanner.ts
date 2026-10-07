export type UiProspectDismissalBannerProps = {
  reason: string | null
  isDismissedByApp: boolean
  isRestoring: boolean
}

export type UiProspectDismissalBannerEmits = {
  restore: []
}
