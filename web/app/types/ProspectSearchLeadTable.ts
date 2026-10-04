import type { ProspectSearchCandidate } from '~/types/ProspectSearch'

export type ProspectSearchLeadTableProps = {
  candidates: ProspectSearchCandidate[]
  selectedCandidateIds?: number[]
}

export type ProspectSearchLeadTableEmits = {
  open: [candidate: ProspectSearchCandidate]
  accept: [candidate: ProspectSearchCandidate]
  reject: [candidate: ProspectSearchCandidate]
  toggleSelect: [candidate: ProspectSearchCandidate]
  toggleSelectAll: [checked: boolean]
}
