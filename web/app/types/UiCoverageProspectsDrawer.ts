import type { CoverageZone } from '~/types/DrawerStack'

/**
 * Props for the UiCoverageProspectsDrawer component (light prospect recap of a
 * coverage-map zone — one city, or a region's covered cities).
 */
export type UiCoverageProspectsDrawerProps = {
  /** Whether the drawer is open. */
  open: boolean
  /** Whether to show the "back" affordance (drawer stacked on another). */
  showBack: boolean
  /** Zone whose prospects are listed (null when closed). */
  zone: CoverageZone | null
}
