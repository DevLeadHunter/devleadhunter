import type { UiUnitChartTone } from '~/types/UiUnitChart'

export const UNIT_CHART_TONE_CLASSES: Record<UiUnitChartTone, string> = {
  ink: 'bg-[var(--app-ink)]',
  green: 'bg-[var(--app-green)]',
  blue: 'bg-[var(--app-blue)]',
  violet: 'bg-[var(--app-violet)]',
  red: 'bg-[var(--app-red)]',
  neutral: 'bg-[color-mix(in_srgb,var(--app-faint)_55%,var(--app-surface))]',
  outline: 'border border-[var(--app-faint)]',
  dashed: 'border border-dashed border-[var(--app-faint)]',
}
