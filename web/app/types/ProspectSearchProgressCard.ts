import type { ProspectSearchSummary } from '~/types/ProspectSearch'

export type ProspectSearchProgressCardProps = {
  search: ProspectSearchSummary
  isCancelling: boolean
  isResuming: boolean
}

export type ProspectSearchProgressCardEmits = {
  cancel: []
  resume: []
}

export type ProspectSearchTradeProgress = {
  key: string
  label: string
  keptLabel: string
  keptCount: number
  wantedCount: number
  keptPercentage: number
  counterLabels: string[]
  stopReasonLabel: string | null
  townsLabel: string | null
}
