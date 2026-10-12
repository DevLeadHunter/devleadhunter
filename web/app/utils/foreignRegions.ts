/**
 * Region choropleth outside France — cantons (CH), provinces (BE), districts (LU) and Québec's 17 administrative
 * regions (CA): static contours + point-in-region lookup.
 */

import type { Feature, FeatureCollection, MultiPolygon, Polygon } from 'geojson'
import type { RegionContourFeature } from '~/utils/regionContours'
import { RegionContours } from '~/utils/regionContours'

/** Properties carried by each foreign region feature (region code, display name, ISO alpha-2 country). */
export type ForeignRegionProperties = {
  code: string
  name: string
  country: string
}

/** One foreign region contour. */
export type ForeignRegionFeature = Feature<Polygon | MultiPolygon, ForeignRegionProperties>

/** Every foreign region contour served from the public folder, merged into one collection. */
export type ForeignRegionCollection = FeatureCollection<Polygon | MultiPolygon, ForeignRegionProperties>

/**
 * Contour files, matched on `code`: ISO 3166-2 for CH/BE/LU (Natural Earth), `CA-QC-01` to `CA-QC-17` for the
 * Québec regions (Découpages administratifs, © Gouvernement du Québec, CC BY 4.0, simplified).
 */
const FOREIGN_REGION_FILES: string[] = ['/regions-ch-be-lu.geojson', '/regions-ca-qc.geojson']

/**
 * Whether a contour carries what a foreign region needs: its display name and its country.
 * @param feature - A contour read from one of the files.
 * @returns True for a usable foreign region.
 */
function isForeignRegion(feature: RegionContourFeature): feature is ForeignRegionFeature {
  return typeof feature.properties.name === 'string' && typeof feature.properties.country === 'string'
}

/**
 * Fetch every foreign region contour from the public folder; one missing file never hides the others.
 * @returns The merged collection, or null when no file could be loaded.
 */
export async function fetchForeignRegions(): Promise<ForeignRegionCollection | null> {
  const files: RegionContourFeature[][] = await Promise.all(
    FOREIGN_REGION_FILES.map((url: string): Promise<RegionContourFeature[]> => RegionContours.read(url)),
  )
  const features: ForeignRegionFeature[] = files.flat().filter(isForeignRegion)
  return features.length > 0 ? { type: 'FeatureCollection', features } : null
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

/**
 * Count the regions (cantons/provinces/districts) a country is divided into.
 * @param collection - The region contours from `fetchForeignRegions`.
 * @param country - ISO alpha-2 country code (e.g. « CH »).
 * @returns The number of regions belonging to that country.
 */
export function countryRegionCount(collection: ForeignRegionCollection, country: string): number {
  return collection.features.filter((feature: ForeignRegionFeature): boolean => feature.properties.country === country)
    .length
}

/**
 * Bounding box of a country, from its region contours, for map framing.
 * @param collection - The region contours from `fetchForeignRegions`.
 * @param country - ISO alpha-2 country code (e.g. « BE »).
 * @returns The [[minLng, minLat], [maxLng, maxLat]] box, or null when the country is absent.
 */
export function countryBounds(
  collection: ForeignRegionCollection,
  country: string,
): [[number, number], [number, number]] | null {
  let minLng: number = Infinity
  let minLat: number = Infinity
  let maxLng: number = -Infinity
  let maxLat: number = -Infinity
  let found: boolean = false

  /**
   * Walk a nested coordinate array down to its [lng, lat] leaves, growing the box.
   * @param node - A coordinate, ring, polygon or multipolygon array.
   */
  function scan(node: unknown): void {
    if (Array.isArray(node) && typeof node[0] === 'number' && typeof node[1] === 'number') {
      minLng = Math.min(minLng, node[0])
      maxLng = Math.max(maxLng, node[0])
      minLat = Math.min(minLat, node[1])
      maxLat = Math.max(maxLat, node[1])
      return
    }
    if (Array.isArray(node)) for (const child of node) scan(child)
  }

  for (const feature of collection.features) {
    if (feature.properties.country !== country) continue
    found = true
    scan(feature.geometry.coordinates)
  }
  return found
    ? [
        [minLng, minLat],
        [maxLng, maxLat],
      ]
    : null
}
