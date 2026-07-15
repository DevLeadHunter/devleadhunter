/**
 * Accent variants for {@link UiStatCardProps} — drives the icon tile + icon colour.
 */
export type UiStatCardAccent = 'neutral' | 'emerald' | 'danger' | 'sky'

/**
 * Props for the UiStatCard component (KPI tile).
 */
export interface UiStatCardProps {
  /** Short metric label (e.g. "Total Prospects"). */
  label: string
  /** Metric value to display (rendered with tabular figures). */
  value: number | string
  /** Lucide icon name (e.g. "i-lucide-users"). */
  icon: string
  /** Colour accent of the icon tile. */
  accent?: UiStatCardAccent
}
