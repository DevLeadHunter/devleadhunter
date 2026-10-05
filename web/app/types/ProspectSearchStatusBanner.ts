import type { ProspectSearchSummary } from '~/types/ProspectSearch'

export type ProspectSearchStatusBannerProps = {
  search: ProspectSearchSummary
  queuedSearches: ProspectSearchSummary[]
  latestJournalMessage: string | null
  isCancelling: boolean
}

export type ProspectSearchStatusBannerEmits = {
  follow: []
  cancel: []
}
