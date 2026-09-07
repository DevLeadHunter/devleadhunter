/**
 * Types of the `UiPeriodFilter` component — a period picker (presets + a custom
 * date range) used to slice a list by date. Kept domain-agnostic so it can filter
 * any dated list, not just campaigns.
 */

/** Which period is selected. `custom` carries an explicit `start`/`end` range. */
export type PeriodPreset = 'all' | 'week' | 'month' | '30d' | 'custom'

/**
 * The selected period. `start`/`end` are `YYYY-MM-DD` local dates, only set when
 * `preset === 'custom'` (both `null` otherwise).
 */
export type PeriodValue = {
  preset: PeriodPreset
  start: string | null
  end: string | null
}

/** Props of the `UiPeriodFilter` component. */
export type UiPeriodFilterProps = {
  modelValue: PeriodValue
}
