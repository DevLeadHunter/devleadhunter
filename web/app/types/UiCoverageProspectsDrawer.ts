import type { CoverageZone } from '~/types/DrawerStack'

/**
 * Light prospect recap of a coverage-map zone: one city, or a region's
 * covered cities.
 */
export type UiCoverageProspectsDrawerProps = {
  open: boolean
  showBack: boolean
  zone: CoverageZone | null
}

export type UiCoverageProspectsDrawerEmits = {
  close: []
  back: []
}
