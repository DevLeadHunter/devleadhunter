/** Properties carried by each city point feature. */
export type CityFeatureProperties = {
  city: string
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
