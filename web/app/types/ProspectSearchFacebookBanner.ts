import type { ProspectSearchFacebookReading } from '~/types/ProspectSearch'

export type ProspectSearchFacebookBannerProps = {
  waitingPageCount: number
  canReadLocally: boolean
  isSearchActive: boolean
  reading: ProspectSearchFacebookReading | null
}

export type ProspectSearchFacebookBannerEmits = {
  retry: []
}

export type ProspectSearchFacebookBannerState =
  | 'needsDesktopApp'
  | 'installingChrome'
  | 'reading'
  | 'failed'
  | 'waitingForResume'
  | 'preparing'
