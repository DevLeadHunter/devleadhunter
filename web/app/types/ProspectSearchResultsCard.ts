import type { ProspectSearchCandidate, ProspectSearchDetail } from '~/types/ProspectSearch'

export type ProspectSearchResultsCardProps = {
  search: ProspectSearchDetail
  busyCandidateIds: number[]
  openingProspectId: number | null
}

export type ProspectSearchResultsCardEmits = {
  'open-prospect': [prospectId: number]
  'keep-candidate': [candidateId: number]
  'reject-candidate': [candidateId: number]
}

export type ProspectSearchRejectedGroup = {
  key: string
  label: string
  candidates: ProspectSearchCandidate[]
}
