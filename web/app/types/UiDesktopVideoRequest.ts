export type UiDesktopVideoRequestProps = {
  isBuildStarted: boolean
  isDesktopAppOnline: boolean
  isWaitingForStoryblokSpace?: boolean
  isCancelling?: boolean
}

export type UiDesktopVideoRequestEmits = {
  cancel: []
}
