/** Props of the daily sending-volume chart (bars + opened line). */
export type EmailHealthVolumeChartProps = {
  /** ISO dates, one per day. */
  labels: string[]
  /** Emails sent per day (background bar). */
  sent: number[]
  /** Emails delivered per day (filled portion of the bar). */
  delivered: number[]
  /** Emails opened per day (line with dots). */
  opened: number[]
}
