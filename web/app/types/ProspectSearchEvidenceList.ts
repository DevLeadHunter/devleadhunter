import type { ProspectSearchEvidenceLine } from '~/types/ProspectSearch'

export type ProspectSearchEvidenceListProps = {
  evidence: ProspectSearchEvidenceLine[]
}

export type ProspectSearchDisplayedEvidence = {
  key: string
  factLabel: string
  value: string
  source: string
  sourceHref: string | null
  snippet: string | null
}
