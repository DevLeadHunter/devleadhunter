import type { DashboardAccent } from '~/utils/dashboardTheme'

/** Props for the DashboardRadialRate component. */
export interface DashboardRadialRateProps {
  /** Percentage value between 0 and 100. */
  value: number
  /** Label shown under the ring. */
  label: string
  /** Accent color key for the progress arc. */
  accent?: DashboardAccent
  /** Optional secondary line (e.g. "4 / 4"). */
  sublabel?: string | null
}
