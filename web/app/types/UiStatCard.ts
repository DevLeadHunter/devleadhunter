/**
 * Accent variants for {@link UiStatCardProps} — drives the icon tile + icon colour.
 */
export type UiStatCardAccent = 'neutral' | 'emerald' | 'danger' | 'sky'

export type UiStatCardProps = {
  label: string
  value: number | string
  icon: string
  accent?: UiStatCardAccent
}
