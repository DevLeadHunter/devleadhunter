import type { ProspectSearchSummary } from '~/types/ProspectSearch'

export type ProspectSearchStatusBannerProps = {
  search: ProspectSearchSummary
  latestJournalMessage: string | null
  isCancelling: boolean
}

export type ProspectSearchStatusBannerEmits = {
  follow: []
  cancel: []
}
