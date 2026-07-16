import type { CityGeo } from '~/composables/useFranceGeo'
import type { CoverageResponse } from '~/services/dashboardService'

/**
 * Visual variant of the coverage map:
 * - 'compact': dashboard home tab (unchanged historical rendering).
 * - 'full': dedicated coverage page (taller map).
 */
export type DashboardCoverageMapVariant = 'compact' | 'full'

/** Props for the DashboardCoverageMap component. */
export interface DashboardCoverageMapProps {
  /** Rendering variant (default 'compact' — the dashboard tab). */
  variant?: DashboardCoverageMapVariant
  /** Trade filter forwarded to the coverage API (empty = all trades). */
  categories?: string[]
}

/** Payload of the 'loaded' event — lets a host page build side panels. */
export interface DashboardCoverageMapLoadedPayload {
  /** The coverage response for the current scope + trade filter. */
  coverage: CoverageResponse
  /** Geocoding results for the covered cities (normalised key → geo). */
  cityGeo: Record<string, CityGeo | null>
}
