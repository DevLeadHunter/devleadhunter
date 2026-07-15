import type { DashboardAccent } from '~/utils/dashboardTheme'

/** Trend direction for a KPI delta. */
export type DashboardKpiTrend = 'up' | 'down' | 'flat'

/** Props for the DashboardKpiCard component. */
export interface DashboardKpiCardProps {
  /** Short metric label (e.g. "Prospects"). */
  label: string
  /** Pre-formatted metric value (e.g. "48" or "1 250 €"). */
  value: string
  /** Font Awesome icon class for the leading glyph. */
  icon: string
  /** Accent color key. */
  accent?: DashboardAccent
  /** Optional secondary line under the value. */
  hint?: string | null
  /** Optional route — when set the whole card becomes a link. */
  to?: string | null
  /** Optional trend direction shown as a chip. */
  trend?: DashboardKpiTrend | null
  /** Optional trend label (e.g. "+12%"). */
  trendLabel?: string | null
}
