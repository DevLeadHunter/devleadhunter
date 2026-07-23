/** Health status of a deliverability signal. */
export type EmailHealthSignalStatus = 'ok' | 'warn' | 'danger'

/** Props of one big health-signal tile (value + status + sparkline). */
export type EmailHealthSignalTileProps = {
  label: string
  value: string
  unit: string
  status: EmailHealthSignalStatus
  hint: string
  sparkline?: number[]
}
