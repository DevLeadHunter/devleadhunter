/**
 * French geography helpers for the coverage map — region contours + city geocoding,
 * both cached in localStorage. Data source: geo.api.gouv.fr (the same public,
 * key-less API used by the city autocomplete).
 */

/** A decimated region: metropolitan regions only, geometry in [lng, lat] rings. */
export interface FranceRegion {
  code: string
  nom: string
  /** Outer rings only (holes dropped — irrelevant at dashboard scale). */
  rings: Array<Array<[number, number]>>
}

/** Geocoding result for one city. */
export interface CityGeo {
  lng: number
  lat: number
  /** Department code (« 69 », « 2A »…). */
  dept: string
  /** Region code. */
  region: string
}

const REGIONS_CACHE_KEY = 'dlh-fr-regions-v2'
const CITIES_CACHE_KEY = 'dlh-fr-cities-v2'
/** Decimate contour points closer than this (degrees ≈ 3 km — sub-pixel here). */
const DECIMATE_EPS = 0.03

/** In-memory cache so repeated tab opens don't re-parse localStorage. */
let regionsMemo: FranceRegion[] | null = null

/**
 * Read a JSON value from localStorage (null on any failure).
 * @param key - Storage key.
 * @returns The parsed value or null.
 */
function readCache<T>(key: string): T | null {
  if (!import.meta.client) return null
  try {
    const raw: string | null = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

/**
 * Write a JSON value to localStorage (ignore quota/serialize errors).
 * @param key - Storage key.
 * @param value - Value to store.
 */
function writeCache(key: string, value: unknown): void {
  if (!import.meta.client) return
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Ignore — the cache is a best-effort optimisation.
  }
}

/**
 * Decimate a ring: drop points within DECIMATE_EPS of the previous kept point.
 * @param ring - Array of [lng, lat] points.
 * @returns A lighter ring.
 */
function decimateRing(ring: Array<[number, number]>): Array<[number, number]> {
  const out: Array<[number, number]> = []
  let last: [number, number] | null = null
  for (const point of ring) {
    if (last === null || Math.abs(point[0] - last[0]) > DECIMATE_EPS || Math.abs(point[1] - last[1]) > DECIMATE_EPS) {
      out.push(point)
      last = point
    }
  }
  if (out.length > 0 && ring.length > 0) {
    const first = ring[0]
    if (first) out.push(first) // close the ring
  }
  return out
}

/**
 * Load metropolitan region contours (cached). Overseas regions are excluded so
 * the map stays framed on metropolitan France + Corsica.
 * @returns The regions, or an empty array when the API is unreachable.
 */
export async function loadFranceRegions(): Promise<FranceRegion[]> {
  if (regionsMemo) return regionsMemo

  const cached: FranceRegion[] | null = readCache<FranceRegion[]>(REGIONS_CACHE_KEY)
  if (cached && cached.length > 0) {
    regionsMemo = cached
    return cached
  }

  interface GeoFeature {
    properties: { code: string; nom: string }
    geometry: { type: string; coordinates: unknown }
  }
  interface GeoCollection {
    features: GeoFeature[]
  }

  try {
    const data: GeoCollection = await $fetch<GeoCollection>('https://geo.api.gouv.fr/regions', {
      query: { fields: 'nom,code,contour', format: 'geojson', geometry: 'contour' },
    })
    const regions: FranceRegion[] = []
    for (const feature of data.features ?? []) {
      const code: string = feature.properties.code
      // Metropolitan region codes are >= 11; overseas are 01-06.
      if (Number(code) < 11) continue
      const rings: Array<Array<[number, number]>> = []
      const geom = feature.geometry
      const polygons: unknown[] = geom.type === 'MultiPolygon' ? (geom.coordinates as unknown[]) : [geom.coordinates]
      for (const polygon of polygons) {
        const ringSet = polygon as Array<Array<[number, number]>>
        const outer = ringSet[0]
        if (outer) rings.push(decimateRing(outer))
      }
      regions.push({ code, nom: feature.properties.nom, rings })
    }
    regionsMemo = regions
    writeCache(REGIONS_CACHE_KEY, regions)
    return regions
  } catch {
    return []
  }
}

/**
 * Normalise a city name for cache keys (lowercase, no accents, trimmed).
 * @param city - Raw city name.
 * @returns The normalised key.
 */
function cityKey(city: string): string {
  return city.trim().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
}

/**
 * Geocode a batch of city names to coordinates + department/region codes,
 * using a persistent cache and bounded concurrency. Unknown cities resolve to
 * null (and are cached as such so they are not retried).
 * @param cities - City names to resolve.
 * @returns A map of normalised city key → geo (or null).
 */
export async function geocodeCities(cities: string[]): Promise<Record<string, CityGeo | null>> {
  const cache: Record<string, CityGeo | null> = readCache<Record<string, CityGeo | null>>(CITIES_CACHE_KEY) ?? {}
  const unique: string[] = [...new Set(cities.map(cityKey))].filter((key: string): boolean => !(key in cache))

  interface Commune {
    centre?: { coordinates?: [number, number] }
    codeDepartement?: string
    codeRegion?: string
  }

  const CONCURRENCY = 6
  let cursor = 0
  let dirty = false

  /**
   * Drain the shared cursor, geocoding one city per iteration.
   * @returns A promise resolved when no city is left to process.
   */
  async function worker(): Promise<void> {
    while (cursor < unique.length) {
      const key: string = unique[cursor++] as string
      try {
        const results: Commune[] = await $fetch<Commune[]>('https://geo.api.gouv.fr/communes', {
          query: { nom: key, fields: 'centre,codeDepartement,codeRegion', boost: 'population', limit: 1 },
        })
        const top: Commune | undefined = results[0]
        const coords: [number, number] | undefined = top?.centre?.coordinates
        cache[key] =
          top && coords
            ? { lng: coords[0], lat: coords[1], dept: top.codeDepartement ?? '', region: top.codeRegion ?? '' }
            : null
      } catch {
        cache[key] = null
      }
      dirty = true
    }
  }

  await Promise.all(Array.from({ length: Math.min(CONCURRENCY, unique.length) }, (): Promise<void> => worker()))
  if (dirty) writeCache(CITIES_CACHE_KEY, cache)
  return cache
}

/** Look up a city in a resolved geocoding map. */
export function lookupCity(map: Record<string, CityGeo | null>, city: string): CityGeo | null {
  return map[cityKey(city)] ?? null
}
