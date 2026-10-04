import type { ProspectSearchSummary } from '~/types/ProspectSearch'

export type ProspectSearchRecentListProps = {
  searches: ProspectSearchSummary[]
  selectedSearchId: number | null
  loadingSearchId: number | null
}

export type ProspectSearchRecentListEmits = {
  select: [searchId: number]
}
