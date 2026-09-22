/** Canton/province choropleth for Belgium, Switzerland and Luxembourg: static contours + point-in-region lookup. */

import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson'

/** Properties carried by each foreign region feature (ISO 3166-2 code, display name, ISO alpha-2 country). */
export type ForeignRegionProperties = {
  code: string
  name: string
  country: string
}

/** The Belgium/Switzerland/Luxembourg region contours served from the public folder. */
export type ForeignRegionCollection = FeatureCollection<Polygon | MultiPolygon, ForeignRegionProperties>

/** Cantons (CH), provinces (BE) and districts (LU), matched on the ISO 3166-2 `code`. */
const FOREIGN_REGIONS_URL: string = '/regions-ch-be-lu.geojson'

/** Loaded once then reused: the contours never change during a session. */
let cachedCollection: ForeignRegionCollection | null = null

/**
 * Fetch the foreign region contours from the public folder, cached for the session.
 * @returns The region collection, or null when the file cannot be loaded.
 */
export async function fetchForeignRegions(): Promise<ForeignRegionCollection | null> {
  if (cachedCollection) return cachedCollection
  try {
    cachedCollection = await $fetch<ForeignRegionCollection>(FOREIGN_REGIONS_URL)
    return cachedCollection
  } catch {
    return null
  }
}

/**
 * Ray-casting test of a point against one linear ring.
 * @param lng - Point longitude.
 * @param lat - Point latitude.
 * @param ring - Closed ring as [lng, lat] pairs.
 * @returns True when the point lies inside the ring.
 */
function isPointInRing(lng: number, lat: number, ring: number[][]): boolean {
  let inside: boolean = false
  for (let i: number = 0, j: number = ring.length - 1; i < ring.length; j = i++) {
    const xi: number = ring[i]?.[0] ?? 0
    const yi: number = ring[i]?.[1] ?? 0
    const xj: number = ring[j]?.[0] ?? 0
    const yj: number = ring[j]?.[1] ?? 0
    const crosses: boolean = yi > lat !== yj > lat && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi
    if (crosses) inside = !inside
  }
  return inside
}

/**
 * Test a point against one polygon: inside its outer ring, outside its holes.
 * XOR across every ring naturally subtracts holes (enclaves) from the area.
 * @param lng - Point longitude.
 * @param lat - Point latitude.
 * @param rings - Polygon rings (outer ring first, holes after).
 * @returns True when the point lies inside the polygon.
 */
function isPointInPolygon(lng: number, lat: number, rings: number[][][]): boolean {
  let inside: boolean = false
  for (const ring of rings) if (isPointInRing(lng, lat, ring)) inside = !inside
  return inside
}

/**
 * Resolve the foreign region (canton/province/district) a coordinate falls in.
 * @param collection - The region contours from `fetchForeignRegions`.
 * @param lng - Point longitude.
 * @param lat - Point latitude.
 * @returns The containing region's properties, or null when outside every region.
 */
export function foreignRegionAt(
  collection: ForeignRegionCollection,
  lng: number,
  lat: number,
): ForeignRegionProperties | null {
  for (const feature of collection.features) {
    const geometry: Polygon | MultiPolygon = feature.geometry
    const hit: boolean =
      geometry.type === 'Polygon'
        ? isPointInPolygon(lng, lat, geometry.coordinates)
        : geometry.coordinates.some((polygon: number[][][]): boolean => isPointInPolygon(lng, lat, polygon))
    if (hit) return feature.properties
  }
  return null
}
