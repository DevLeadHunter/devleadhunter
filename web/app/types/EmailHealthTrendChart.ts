/** Color tones resolved to Atelier CSS variables inside the chart. */
export type EmailHealthChartTone = 'green' | 'red' | 'amber' | 'blue' | 'ink'

/** One plotted series. */
export type EmailHealthChartSeries = {
  key: string
  label: string
  tone: EmailHealthChartTone
  values: number[]
  area?: boolean
}

/** A horizontal threshold guide (e.g. the 0.3 % Gmail complaint ceiling). */
export type EmailHealthChartThreshold = {
  value: number
  label: string
  tone: EmailHealthChartTone
}

/** Props of the smooth multi-series trend chart. */
export type EmailHealthTrendChartProps = {
  labels: string[]
  series: EmailHealthChartSeries[]
  thresholds?: EmailHealthChartThreshold[]
  unit?: string
}
