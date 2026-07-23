/**
 * Shared prospection-coverage store — owns the coverage data (scope + trade
 * filter + geocoded cities) so the coverage page, the map and the coverage
 * drawers (filters, zone prospects) all read the same state.
 */
import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { CityGeo } from '~/composables/useFranceGeo'
import { geocodeCities, lookupCity } from '~/composables/useFranceGeo'
import type { CoverageResponse } from '~/services/dashboardService'
import { getCoverage } from '~/services/dashboardService'
import type { FranceMajorCity } from '~/utils/franceTerritory'
import { FRANCE_MAJOR_CITIES, FRANCE_REGIONS } from '~/utils/franceTerritory'

/**
 * Normalise a city name for comparison (lowercase, accent-free, trimmed).
 * @param name - Raw city name.
 * @returns The comparable key.
 */
export function normalizeCityName(name: string): string {
  return name.trim().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
}

export const useCoverageStore = defineStore('coverage', () => {
  /** Coverage scope: 'me' | 'org' | 'member:{id}'. */
  const scope: Ref<string> = ref('me')

  /** Selected trades — empty means « all trades » (no filter). */
  const selectedCategories: Ref<string[]> = ref([])

  /** Last coverage response for the current scope + filter. */
  const coverage: Ref<CoverageResponse | null> = ref(null)

  /** Geocoding results for the covered cities. */
  const cityGeo: Ref<Record<string, CityGeo | null>> = ref({})

  const isLoading: Ref<boolean> = ref(false)

  /** True once the first load happened (gates « all done » empty states). */
  const hasLoaded: Ref<boolean> = ref(false)

  /** Trades available in the scope — sticky so the filter UI never flickers. */
  const availableCategories: Ref<string[]> = ref([])

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
   * Load coverage for the current scope + trade filter, then geocode cities.
   * @returns A promise resolved once loaded.
   */
  async function load(): Promise<void> {
    isLoading.value = true
    try {
      const [scopeName, memberId] = parseScope(scope.value)
      const data: CoverageResponse = await getCoverage(scopeName, memberId, selectedCategories.value)
      coverage.value = data
      if (data.available_categories.length > 0) availableCategories.value = data.available_categories
      cityGeo.value = await geocodeCities(data.cities.map((c): string => c.city))
    } catch {
      coverage.value = {
        scope: scope.value,
        cities: [],
        total_prospects: 0,
        members: coverage.value?.members ?? [],
        available_categories: availableCategories.value,
      }
    } finally {
      isLoading.value = false
      hasLoaded.value = true
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

  /** INSEE region codes covered by at least one prospected city. */
  const coveredRegionCodes: ComputedRef<Set<string>> = computed((): Set<string> => {
    const covered = new Set<string>()
    for (const city of coverage.value?.cities ?? []) {
      const geo: CityGeo | null = lookupCity(cityGeo.value, city.city)
      if (geo && geo.region) covered.add(geo.region)
    }
    return covered
  })

  /** Names of the metropolitan regions with zero prospected city. */
  const uncoveredRegions: ComputedRef<string[]> = computed((): string[] =>
    Object.entries(FRANCE_REGIONS)
      .filter(([code]): boolean => !coveredRegionCodes.value.has(code))
      .map(([, name]): string => name),
  )

  /** Prospected city names, normalised. */
  const coveredCityNames: ComputedRef<Set<string>> = computed((): Set<string> => {
    const names = new Set<string>()
    for (const city of coverage.value?.cities ?? []) names.add(normalizeCityName(city.city))
    return names
  })

  /** Major cities never prospected (biggest first), capped for the panels. */
  const suggestedCities: ComputedRef<FranceMajorCity[]> = computed((): FranceMajorCity[] =>
    FRANCE_MAJOR_CITIES.filter((city): boolean => !coveredCityNames.value.has(normalizeCityName(city.name))).slice(
      0,
      10,
    ),
  )

  /**
   * Covered city names belonging to one region (raw names, for zone queries).
   * @param regionCode - INSEE region code.
   * @returns The prospected city names of that region.
   */
  function coveredCitiesOfRegion(regionCode: string): string[] {
    const cities: string[] = []
    for (const city of coverage.value?.cities ?? []) {
      const geo: CityGeo | null = lookupCity(cityGeo.value, city.city)
      if (geo && geo.region === regionCode) cities.push(city.city)
    }
    return cities
  }

  return {
    scope,
    selectedCategories,
    coverage,
    cityGeo,
    isLoading,
    hasLoaded,
    availableCategories,
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
