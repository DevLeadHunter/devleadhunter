import type { ProspectSearchCandidate } from '~/types/ProspectSearch'
import type { StatusPresentation } from '~/types/StatusPresentation'

export type ProspectSearchCandidateRowProps = {
  candidate: ProspectSearchCandidate
  tradeLabel: string
  isBusy: boolean
  isOpeningProspect: boolean
}

export type ProspectSearchCandidateRowEmits = {
  'open-prospect': [prospectId: number]
  keep: [candidateId: number]
  reject: [candidateId: number]
}

export type ProspectSearchCandidateLink = {
  key: string
  label: string
  href: string
  icon: string
  warning: StatusPresentation | null
}
