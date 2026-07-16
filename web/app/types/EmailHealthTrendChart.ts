/** Color tones resolved to Atelier CSS variables inside the chart. */
export type EmailHealthChartTone = 'green' | 'red' | 'amber' | 'blue' | 'ink'

/** One plotted series. */
export interface EmailHealthChartSeries {
  key: string
  label: string
  tone: EmailHealthChartTone
  values: number[]
  /** Draw a soft gradient area under the line. */
  area?: boolean
}

/** A horizontal threshold guide (e.g. the 0.3 % Gmail complaint ceiling). */
export interface EmailHealthChartThreshold {
  value: number
  label: string
  tone: EmailHealthChartTone
}

/** Props of the smooth multi-series trend chart. */
export interface EmailHealthTrendChartProps {
  /** ISO dates, one per point (shared by every series). */
  labels: string[]
  series: EmailHealthChartSeries[]
  thresholds?: EmailHealthChartThreshold[]
  /** Display unit appended to values ('' or '%'). */
  unit?: string
}
