import type { ProspectSearchTradeCounts } from '~/types/ProspectSearch'

export type ProspectSearchTradeProgressListProps = {
  tradeCounts: ProspectSearchTradeCounts[]
  shouldShowDetails?: boolean
}

export type ProspectSearchTradeProgress = {
  key: string
  label: string
  foundCount: number
  wantedCount: number
  foundPercentage: number
  counterLabels: string[]
  stopReasonLabel: string | null
  townsLabel: string | null
}
