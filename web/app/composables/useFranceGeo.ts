/** French geocoding for the coverage map (geo.api.gouv.fr, localStorage cache). Region contours are loaded by MapLibre, not here. */

/** Geocoding result for one city. */
export type CityGeo = {
  lng: number
  lat: number
  dept: string
  region: string
}

const CITIES_CACHE_KEY = 'dlh-fr-cities-v2'

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

  type Commune = {
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

/** Commune resolved from a map click (reverse geocoding). */
export type ReverseGeocodedCommune = {
  name: string
  dept: string
  region: string
}

/**
 * Resolve the commune under a map coordinate (reverse geocoding) — used by the
 * coverage map to prefill a prospect search from a click on the basemap.
 * Same public key-less API as the forward geocoding; null on miss/error.
 * @param lng - Longitude of the clicked point.
 * @param lat - Latitude of the clicked point.
 * @returns The commune at this point, or null.
 */
export async function reverseGeocodeCommune(lng: number, lat: number): Promise<ReverseGeocodedCommune | null> {
  type Commune = {
    nom?: string
    codeDepartement?: string
    codeRegion?: string
  }
  try {
    const results: Commune[] = await $fetch<Commune[]>('https://geo.api.gouv.fr/communes', {
      query: { lat, lon: lng, fields: 'nom,codeDepartement,codeRegion' },
    })
    const top: Commune | undefined = results[0]
    if (!top?.nom) return null
    return { name: top.nom, dept: top.codeDepartement ?? '', region: top.codeRegion ?? '' }
  } catch {
    return null
  }
}
