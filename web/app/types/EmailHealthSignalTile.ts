/** Health status of a deliverability signal. */
export type EmailHealthSignalStatus = 'ok' | 'warn' | 'danger'

/** Props of one big health-signal tile (value + status + sparkline). */
export type EmailHealthSignalTileProps = {
  label: string
  /** Already-formatted value (e.g. "0,12"). */
  value: string
  unit: string
  status: EmailHealthSignalStatus
  hint: string
  /** Daily values for the mini sparkline (optional). */
  sparkline?: number[]
}
