/** compact = prospect list ; default = prospect card. */
export type UiCountryFlagSize = 'compact' | 'default'

export type UiCountryFlagProps = {
  code?: string | null
  hideFrance?: boolean
  size?: UiCountryFlagSize
  title?: string
}
