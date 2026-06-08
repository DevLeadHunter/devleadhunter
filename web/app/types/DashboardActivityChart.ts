import type { ActivityPoint } from '~/services/dashboardService'

/** Props for the DashboardActivityChart component. */
export interface DashboardActivityChartProps {
  /** Daily activity points, ordered oldest → newest. */
  points: ActivityPoint[]
}
