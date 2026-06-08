import type { DashboardAccent } from '~/utils/dashboardTheme'

/** A single stage of the conversion funnel. */
export interface FunnelStage {
  /** Stage label (e.g. "Emails ouverts"). */
  label: string
  /** Raw count for this stage. */
  value: number
  /** Accent color key for the bar. */
  accent?: DashboardAccent
}

/** Props for the DashboardConversionFunnel component. */
export interface DashboardConversionFunnelProps {
  /** Ordered funnel stages, from widest (top) to narrowest (bottom). */
  stages: FunnelStage[]
}
