/** Geocoding for the coverage map: France via geo.api.gouv.fr, Belgium/Switzerland/Luxembourg via Photon (OSM), localStorage cache. Region contours are loaded by MapLibre, not here. */

import { ProspectCountries } from '~/utils/prospectCountries'

/**
 * Geocoding result for one city. `insee`/`dept`/`region` are France-only (empty for
 * foreign cities): they feed the department/region stats and the BAN street lookup.
 */
export type CityGeo = {
  lng: number
  lat: number
  insee: string
  dept: string
  region: string
}

const CITIES_CACHE_KEY: string = 'dlh-cities-v5'

/** Parallel requests allowed against the public geocoding APIs. */
const GEOCODING_CONCURRENCY: number = 6

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
 * Normalise a country to an ISO alpha-2 code (upper), defaulting blanks to « FR ».
 * @param country - Raw country value.
 * @returns The 2-letter country code.
 */
function normalizeCountryCode(country: string | null | undefined): string {
  const code: string = (country ?? '').trim().toUpperCase()
  return code || 'FR'
}

/**
 * Build the cache/lookup key of a city, scoped by country so cross-border homonyms (Fribourg FR vs CH) never collide.
 * @param city - Raw city name.
 * @param country - Raw country value.
 * @returns The composite key « <cc>:<city> ».
 */
function cityCountryKey(city: string, country: string): string {
  return `${normalizeCountryCode(country).toLowerCase()}:${cityKey(city)}`
}

/**
 * Run one geocoding task per item, never more than `GEOCODING_CONCURRENCY` at a time.
 * @param items - Items to process, in order.
 * @param resolveOne - Task run for a single item; it is expected to swallow its own failures.
 * @returns A promise resolved once every item has been processed.
 */
async function runBoundedGeocoding<T>(items: T[], resolveOne: (item: T) => Promise<void>): Promise<void> {
  let cursor: number = 0

  /**
   * Drain the shared cursor, processing one item per iteration.
   * @returns A promise resolved when no item is left to process.
   */
  async function worker(): Promise<void> {
    while (cursor < items.length) {
      await resolveOne(items[cursor++] as T)
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(GEOCODING_CONCURRENCY, items.length) }, (): Promise<void> => worker()),
  )
}

/** One city to geocode: its name plus the country that disambiguates it. */
export type GeocodableCity = {
  city: string
  country: string
}

/**
 * Geocode one French commune through geo.api.gouv.fr (name search, population boost).
 * @param city - Raw city name.
 * @returns The commune centre with its INSEE/department/region codes, or null.
 */
async function geocodeFrenchCity(city: string): Promise<CityGeo | null> {
  type Commune = {
    code?: string
    nom?: string
    centre?: { coordinates?: [number, number] }
    codeDepartement?: string
    codeRegion?: string
  }
  const key: string = cityKey(city)
  try {
    const results: Commune[] = await $fetch<Commune[]>('https://geo.api.gouv.fr/communes', {
      query: { nom: key, fields: 'code,nom,centre,codeDepartement,codeRegion', boost: 'population', limit: 5 },
    })
    // « Betton » remontait Betton-Bettonet (306 hab., Savoie) : le nom exact prime sur le score flou.
    const exact: Commune | undefined = results.find((commune: Commune): boolean => cityKey(commune.nom ?? '') === key)
    const top: Commune | undefined = exact ?? results[0]
    const coords: [number, number] | undefined = top?.centre?.coordinates
    if (!top || !coords) return null
    return {
      lng: coords[0],
      lat: coords[1],
      insee: top.code ?? '',
      dept: top.codeDepartement ?? '',
      region: top.codeRegion ?? '',
    }
  } catch {
    return null
  }
}

/** Public multi-country geocoder (Komoot/OSM), used for cities outside France. */
const PHOTON_URL: string = 'https://photon.komoot.io/api/'

/** One Photon result — only the fields the city lookup needs. */
type PhotonFeature = {
  geometry?: { coordinates?: [number, number] }
  properties?: { name?: string; countrycode?: string }
}

/**
 * Geocode a city outside France through Photon, filtered to the requested country so a homonym elsewhere is never placed.
 * @param city - Raw city name.
 * @param countryCode - ISO alpha-2 country code (upper, e.g. « CH »).
 * @returns The city centre (no INSEE/region, which are France-only), or null.
 */
async function geocodeForeignCity(city: string, countryCode: string): Promise<CityGeo | null> {
  try {
    const label: string = ProspectCountries.option(countryCode).label
    const response: { features?: PhotonFeature[] } = await $fetch<{ features?: PhotonFeature[] }>(PHOTON_URL, {
      query: { q: `${city}, ${label}`, limit: 5, lang: 'fr' },
    })
    const inCountry: PhotonFeature[] = (response.features ?? []).filter(
      (feature: PhotonFeature): boolean => (feature.properties?.countrycode ?? '').toUpperCase() === countryCode,
    )
    if (inCountry.length === 0) return null
    const wanted: string = cityKey(city)
    const exact: PhotonFeature | undefined = inCountry.find(
      (feature: PhotonFeature): boolean => cityKey(feature.properties?.name ?? '') === wanted,
    )
    const coords: [number, number] | undefined = (exact ?? inCountry[0])?.geometry?.coordinates
    if (!coords) return null
    return { lng: coords[0], lat: coords[1], insee: '', dept: '', region: '' }
  } catch {
    return null
  }
}

/**
 * Geocode a batch of cities, routing each to its country's geocoder; cached, unknown cities resolve to null.
 * @param cities - City + country pairs to resolve.
 * @returns A map of « <cc>:<city> » key → geo (or null).
 */
export async function geocodeCities(cities: GeocodableCity[]): Promise<Record<string, CityGeo | null>> {
  const cache: Record<string, CityGeo | null> = readCache<Record<string, CityGeo | null>>(CITIES_CACHE_KEY) ?? {}
  const seen: Set<string> = new Set<string>()
  const pending: GeocodableCity[] = []
  for (const entry of cities) {
    const key: string = cityCountryKey(entry.city, entry.country)
    if (key in cache || seen.has(key)) continue
    seen.add(key)
    pending.push(entry)
  }
  if (pending.length === 0) return cache

  await runBoundedGeocoding(pending, async (entry: GeocodableCity): Promise<void> => {
    const code: string = normalizeCountryCode(entry.country)
    cache[cityCountryKey(entry.city, entry.country)] =
      code === 'FR' ? await geocodeFrenchCity(entry.city) : await geocodeForeignCity(entry.city, code)
  })

  writeCache(CITIES_CACHE_KEY, cache)
  return cache
}

/**
 * Look up a city in a resolved geocoding map.
 * @param map - The map returned by `geocodeCities`.
 * @param city - Raw city name.
 * @param country - Raw country value (routed to the same key as geocoding).
 * @returns The geo, or null when absent/unresolved.
 */
export function lookupCity(map: Record<string, CityGeo | null>, city: string, country: string): CityGeo | null {
  return map[cityCountryKey(city, country)] ?? null
}

/** Coordinates of one prospect address. */
export type AddressGeo = {
  lng: number
  lat: number
}

/** One prospect to place on the map: its street line (may be empty), plus the city and country it belongs to. */
export type GeocodableAddress = {
  address: string | null
  city: string
  country: string
}

/** One BAN lookup: the free-text query plus the commune it must stay inside. */
type AddressQuery = {
  key: string
  query: string
  insee: string
}

const ADDRESSES_CACHE_KEY: string = 'dlh-fr-addresses-v1'

/** Below this score, the BAN match is too loose to be trusted as a street position. */
const MIN_ADDRESS_SCORE: number = 0.4

/**
 * Build the cache key of a street address (country + address + city, normalised).
 * @param address - Street part, may be empty.
 * @param city - City the prospect belongs to.
 * @param country - Country the prospect belongs to (keeps cross-border homonyms apart).
 * @returns The normalised key.
 */
export function addressKey(address: string | null | undefined, city: string, country: string): string {
  return `${normalizeCountryCode(country).toLowerCase()}:${cityKey(`${address ?? ''} ${city}`)}`
}

/**
 * Geocode street addresses through the BAN, bounded to each prospect's commune; unplaceable addresses resolve to null.
 * @param addresses - Address + city pairs to resolve.
 * @param cities - Cities already resolved by `geocodeCities`, for their INSEE code.
 * @returns A map of normalised key → coordinates (or null).
 */
export async function geocodeAddresses(
  addresses: GeocodableAddress[],
  cities: Record<string, CityGeo | null>,
): Promise<Record<string, AddressGeo | null>> {
  const cache: Record<string, AddressGeo | null> =
    readCache<Record<string, AddressGeo | null>>(ADDRESSES_CACHE_KEY) ?? {}

  const pending: Map<string, AddressQuery> = new Map<string, AddressQuery>()
  for (const entry of addresses) {
    const street: string = (entry.address ?? '').trim()
    // Sans rue, le BAN renverrait le centre commune : autant laisser le repli ville s'en charger.
    if (!street) continue
    const insee: string = lookupCity(cities, entry.city, entry.country)?.insee ?? ''
    // Commune inconnue (ou ville hors France, sans INSEE) : pas de position de rue, on garde le repli ville.
    if (!insee) continue
    const key: string = addressKey(street, entry.city, entry.country)
    if (key in cache || pending.has(key)) continue
    pending.set(key, { key, query: `${street} ${entry.city}`.trim(), insee })
  }

  type BanFeature = {
    geometry?: { coordinates?: [number, number] }
    properties?: { score?: number }
  }

  const queries: AddressQuery[] = [...pending.values()]
  if (queries.length === 0) return cache

  await runBoundedGeocoding(queries, async ({ key, query, insee }: AddressQuery): Promise<void> => {
    try {
      const response: { features?: BanFeature[] } = await $fetch<{ features?: BanFeature[] }>(
        'https://api-adresse.data.gouv.fr/search/',
        { query: { q: query, citycode: insee, limit: 1 } },
      )
      const top: BanFeature | undefined = response.features?.[0]
      const coords: [number, number] | undefined = top?.geometry?.coordinates
      const score: number = top?.properties?.score ?? 0
      cache[key] = coords && score >= MIN_ADDRESS_SCORE ? { lng: coords[0], lat: coords[1] } : null
    } catch {
      cache[key] = null
    }
  })

  writeCache(ADDRESSES_CACHE_KEY, cache)
  return cache
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
