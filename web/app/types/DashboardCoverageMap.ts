import type { ProspectCountryOption } from '~/utils/prospectCountries'

/** One prospect placed at its own address, or at the city centre when `isPreciseAddress` is false. */
export type ProspectFeatureProperties = {
  prospectId: number
  name: string
  city: string
  isPreciseAddress: boolean
}

/** Properties carried by each city point feature (the country keeps Laval FR and Laval QC apart). */
export type CityFeatureProperties = {
  city: string
  country: string
  count: number
  radius: number
}

/** Choropleth washes drawn over the basemap (amber → green, Atelier palette). */
export type CoverageTierColors = {
  none: string
  low: string
  medium: string
  good: string
  strong: string
}

/** A [[west, south], [east, north]] box in degrees, as MapLibre frames it. */
export type CoverageMapBounds = [[number, number], [number, number]]

/** A country of the selector, with how many prospects the current scope and trades hold there. */
export type CoverageCountryOption = ProspectCountryOption & {
  prospectCount: number
}

/** Per foreign region code: the prospect total and the prospected city names it holds. */
export type ForeignRegionIndex = {
  totals: Record<string, number>
  cities: Record<string, string[]>
}
