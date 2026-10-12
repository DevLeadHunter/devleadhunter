/**
 * Shared prospection-coverage store — scope, trade filter and geocoded cities for the map and drawers.
 */
import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { AddressGeo, CityGeo } from '~/composables/useFranceGeo'
import {
  cityGeoEntries,
  geocodeAddresses,
  hasCityGeo,
  lookupCity,
  runBoundedGeocoding,
} from '~/composables/useFranceGeo'
import type { CityToPlace, CoverageCity, CoverageResponse, PlaceCitiesResponse } from '~/services/dashboardService'
import { DashboardService } from '~/services/dashboardService'
import type { FranceMajorCity } from '~/utils/franceTerritory'
import { FRANCE_MAJOR_CITIES, FRANCE_REGIONS } from '~/utils/franceTerritory'

/** Cities per placement request: a request answers when its slowest city does, so small batches fill the map steadily. */
const PLACEMENT_BATCH_SIZE: number = 3

/** Placement requests in flight at once, kept low so the burst stays under the public geocoders' rate limits. */
const PLACEMENT_PARALLEL_BATCHES: number = 4

/**
 * Normalise a city name for comparison (lowercase, accent-free, trimmed).
 * @param name - Raw city name.
 * @returns The comparable key.
 */
export function normalizeCityName(name: string): string {
  return name.trim().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
}

// Pinia ne fournit pas de type nommé pour un store : TypeScript l'élide, il est inécrivable.
// eslint-disable-next-line @typescript-eslint/typedef
export const useCoverageStore = defineStore('coverage', () => {
  const scope: Ref<string> = ref('me')
  const selectedCategories: Ref<string[]> = ref([])
  const coverage: Ref<CoverageResponse | null> = ref(null)
  const cityGeo: Ref<Record<string, CityGeo | null>> = ref({})
  const addressGeo: Ref<Record<string, AddressGeo | null>> = ref({})
  const isLoading: Ref<boolean> = ref(false)
  const hasLoaded: Ref<boolean> = ref(false)
  const availableCategories: Ref<string[]> = ref([])
  const placingCityCount: Ref<number> = ref(0)
  let latestLoadId: number = 0

  /**
   * Split the scope value into an API scope + optional member id.
   * @param value - 'me' | 'org' | 'member:{id}'.
   * @returns A [scope, memberId] tuple.
   */
  function parseScope(value: string): [string, number | undefined] {
    if (value.startsWith('member:')) return ['member', Number(value.slice('member:'.length))]
    return [value, undefined]
  }

  /**
   * Load coverage for the current scope + trade filter and show it at once; pending cities are placed afterwards.
   * @returns A promise resolved once the coverage is shown, while its cities may still be placed.
   */
  async function load(): Promise<void> {
    const loadId: number = ++latestLoadId
    isLoading.value = true
    const [scopeName, memberId]: [string, number | undefined] = parseScope(scope.value)
    const data: CoverageResponse | null = await DashboardService.getCoverage(
      scopeName,
      memberId,
      selectedCategories.value,
    ).catch((): null => null)
    if (loadId !== latestLoadId) {
      return
    }
    if (data) {
      coverage.value = data
      if (data.available_categories.length > 0) {
        availableCategories.value = data.available_categories
      }
      cityGeo.value = { ...cityGeo.value, ...cityGeoEntries(data.cities) }
    } else {
      coverage.value = {
        scope: scope.value,
        cities: [],
        points: [],
        total_prospects: 0,
        countries: [],
        members: coverage.value?.members ?? [],
        available_categories: availableCategories.value,
      }
    }
    isLoading.value = false
    hasLoaded.value = true
    if (data) {
      placeCoverage(data, loadId)
    }
  }

  /**
   * Place the cities the coverage left pending, then each prospect at its street address.
   * @param data - The coverage answer to complete.
   * @param loadId - The load it belongs to; a newer load stops it.
   * @returns A promise resolved once the cities and the addresses are placed.
   */
  async function placeCoverage(data: CoverageResponse, loadId: number): Promise<void> {
    await placePendingCities(data.cities, loadId)
    if (loadId !== latestLoadId) {
      return
    }
    const resolved: Record<string, AddressGeo | null> = await geocodeAddresses(data.points, cityGeo.value)
    addressGeo.value = { ...addressGeo.value, ...resolved }
  }

  /**
   * Have the API place the cities still pending, French ones first since their geocoder answers at once.
   * @param cities - Cities of the coverage answer.
   * @param loadId - The load they belong to; a newer load stops the placement.
   * @returns A promise resolved once every batch has answered.
   */
  async function placePendingCities(cities: CoverageCity[], loadId: number): Promise<void> {
    const pendingCities: CityToPlace[] = cities
      .filter(
        (city: CoverageCity): boolean =>
          city.geocoding === 'pending' && !hasCityGeo(cityGeo.value, city.city, city.country),
      )
      .sort(
        (first: CoverageCity, second: CoverageCity): number =>
          Number(first.country !== 'FR') - Number(second.country !== 'FR'),
      )
      .map((city: CoverageCity): CityToPlace => ({ city: city.city, country: city.country }))
    const batches: CityToPlace[][] = Array.from(
      { length: Math.ceil(pendingCities.length / PLACEMENT_BATCH_SIZE) },
      (_: unknown, index: number): CityToPlace[] =>
        pendingCities.slice(index * PLACEMENT_BATCH_SIZE, (index + 1) * PLACEMENT_BATCH_SIZE),
    )
    placingCityCount.value = pendingCities.length
    await runBoundedGeocoding(
      batches,
      (batch: CityToPlace[]): Promise<void> => placeCityBatch(batch, loadId),
      PLACEMENT_PARALLEL_BATCHES,
    )
  }

  /**
   * Place one batch of cities and paint them; a failed batch leaves its cities off the map until the next visit.
   * @param batch - Cities sent in one request.
   * @param loadId - The load the batch belongs to.
   * @returns A promise resolved once the batch has answered.
   */
  async function placeCityBatch(batch: CityToPlace[], loadId: number): Promise<void> {
    if (loadId !== latestLoadId) {
      return
    }
    const answer: PlaceCitiesResponse | null = await DashboardService.placeCoverageCities(batch).catch((): null => null)
    if (answer) {
      cityGeo.value = { ...cityGeo.value, ...cityGeoEntries(answer.cities) }
    }
    if (loadId === latestLoadId) {
      placingCityCount.value -= batch.length
    }
  }

  /** Reset the trade filter to « all trades » and reload. */
  function selectAllCategories(): void {
    if (selectedCategories.value.length === 0) return
    selectedCategories.value = []
    void load()
  }

  /**
   * Toggle one trade in the filter and reload.
   * @param category - Trade to toggle.
   */
  function toggleCategory(category: string): void {
    const current: string[] = selectedCategories.value
    selectedCategories.value = current.includes(category)
      ? current.filter((c: string): boolean => c !== category)
      : [...current, category]
    void load()
  }

  const coveredRegionCodes: ComputedRef<Set<string>> = computed((): Set<string> => {
    const covered: Set<string> = new Set<string>()
    for (const city of coverage.value?.cities ?? []) {
      const geo: CityGeo | null = lookupCity(cityGeo.value, city.city, city.country)
      if (geo && geo.region) covered.add(geo.region)
    }
    return covered
  })

  const uncoveredRegions: ComputedRef<string[]> = computed((): string[] =>
    Object.entries(FRANCE_REGIONS)
      .filter(([code]: [string, string]): boolean => !coveredRegionCodes.value.has(code))
      .map(([, name]: [string, string]): string => name),
  )

  const coveredCityNames: ComputedRef<Set<string>> = computed((): Set<string> => {
    const names: Set<string> = new Set<string>()
    for (const city of coverage.value?.cities ?? []) names.add(normalizeCityName(city.city))
    return names
  })

  const suggestedCities: ComputedRef<FranceMajorCity[]> = computed((): FranceMajorCity[] =>
    FRANCE_MAJOR_CITIES.filter(
      (city: FranceMajorCity): boolean => !coveredCityNames.value.has(normalizeCityName(city.name)),
    ).slice(0, 10),
  )

  /**
   * Covered city names belonging to one region (raw names, for zone queries).
   * @param regionCode - INSEE region code.
   * @returns The prospected city names of that region.
   */
  function coveredCitiesOfRegion(regionCode: string): string[] {
    const cities: string[] = []
    for (const city of coverage.value?.cities ?? []) {
      const geo: CityGeo | null = lookupCity(cityGeo.value, city.city, city.country)
      if (geo && geo.region === regionCode) cities.push(city.city)
    }
    return cities
  }

  return {
    scope,
    selectedCategories,
    coverage,
    cityGeo,
    addressGeo,
    isLoading,
    hasLoaded,
    availableCategories,
    placingCityCount,
    load,
    selectAllCategories,
    toggleCategory,
    coveredRegionCodes,
    uncoveredRegions,
    coveredCityNames,
    suggestedCities,
    coveredCitiesOfRegion,
  }
})
