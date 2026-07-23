/** Props of the daily sending-volume chart (bars + opened line). */
export type EmailHealthVolumeChartProps = {
  labels: string[]
  sent: number[]
  delivered: number[]
  opened: number[]
}
