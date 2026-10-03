export type UiKpiBandMeterTone = 'ink' | 'soft' | 'blue' | 'green'

export type UiKpiBandTrend = 'up' | 'down' | 'flat'

export type UiKpiBandTrendBadge = {
  trend: UiKpiBandTrend
  text: string
}

export type UiKpiBandCell = {
  key: string
  label: string
  value: string
  total: string | null
  detail: string
  trendBadge: UiKpiBandTrendBadge | null
  comparisonNote: string
  meterRatio: number
  meterTone: UiKpiBandMeterTone
}

export type UiKpiBandProps = {
  cells: UiKpiBandCell[]
  label: string
}
