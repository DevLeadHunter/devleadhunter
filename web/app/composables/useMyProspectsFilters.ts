import type { Ref } from 'vue'
import type { ProspectWebsiteFilter } from '~/types'
import { ref, watch, onMounted } from 'vue'

/** localStorage key persisting the « Mes prospects » list filters. */
const MY_PROSPECTS_FILTERS_STORAGE_KEY: string = 'dlh-my-prospects-filters'

const WEBSITE_FILTER_VALUES: ProspectWebsiteFilter[] = ['all', 'yes', 'no', 'dead', 'improvable']

export type TemperatureFilter = 'all' | 'hot' | 'warm' | 'cold'
const TEMPERATURE_FILTER_VALUES: TemperatureFilter[] = ['all', 'hot', 'warm', 'cold']

export type EmailFilter = 'all' | 'undeliverable'
const EMAIL_FILTER_VALUES: EmailFilter[] = ['all', 'undeliverable']

/** Persisted filter state for the my-prospects page. */
export type MyProspectsFiltersState = {
  searchQuery: string
  filterCategory: string
  filterCity: string
  filterWebsite: ProspectWebsiteFilter
  filterTemperature: TemperatureFilter
  filterEmail: EmailFilter
  activeTab: 'not_contacted' | 'contacted'
}

/**
 * Default filter state for the my-prospects page.
 * @returns A fresh filter snapshot.
 */
function defaultFilters(): MyProspectsFiltersState {
  return {
    searchQuery: '',
    filterCategory: '',
    filterCity: '',
    filterWebsite: 'no',
    filterTemperature: 'all',
    filterEmail: 'all',
    activeTab: 'not_contacted',
  }
}

/**
 * Parse and validate a stored filter snapshot.
 * @param raw - JSON string from localStorage.
 * @returns A validated state, or null when invalid.
 */
function parseStoredFilters(raw: string): MyProspectsFiltersState | null {
  try {
    const parsed: Partial<MyProspectsFiltersState> = JSON.parse(raw) as Partial<MyProspectsFiltersState>
    const defaults: MyProspectsFiltersState = defaultFilters()
    const filterWebsite: ProspectWebsiteFilter = WEBSITE_FILTER_VALUES.includes(
      parsed.filterWebsite as ProspectWebsiteFilter,
    )
      ? (parsed.filterWebsite as ProspectWebsiteFilter)
      : defaults.filterWebsite
    const activeTab: MyProspectsFiltersState['activeTab'] =
      parsed.activeTab === 'contacted' ? 'contacted' : 'not_contacted'
    const filterTemperature: TemperatureFilter = TEMPERATURE_FILTER_VALUES.includes(
      parsed.filterTemperature as TemperatureFilter,
    )
      ? (parsed.filterTemperature as TemperatureFilter)
      : defaults.filterTemperature
    const filterEmail: EmailFilter = EMAIL_FILTER_VALUES.includes(parsed.filterEmail as EmailFilter)
      ? (parsed.filterEmail as EmailFilter)
      : defaults.filterEmail

    return {
      searchQuery: typeof parsed.searchQuery === 'string' ? parsed.searchQuery : defaults.searchQuery,
      filterCategory: typeof parsed.filterCategory === 'string' ? parsed.filterCategory : defaults.filterCategory,
      filterCity: typeof parsed.filterCity === 'string' ? parsed.filterCity : defaults.filterCity,
      filterWebsite,
      filterTemperature,
      filterEmail,
      activeTab,
    }
  } catch {
    return null
  }
}

/**
 * Reactive filters for « Mes prospects », persisted in localStorage across navigation.
 * @returns Filter refs plus a reset helper.
 */
export function useMyProspectsFilters(): {
  searchQuery: Ref<string>
  filterCategory: Ref<string>
  filterCity: Ref<string>
  filterWebsite: Ref<ProspectWebsiteFilter>
  filterTemperature: Ref<TemperatureFilter>
  filterEmail: Ref<EmailFilter>
  activeTab: Ref<'not_contacted' | 'contacted'>
  clearFilters: () => void
} {
  const defaults: MyProspectsFiltersState = defaultFilters()
  const searchQuery: Ref<string> = ref(defaults.searchQuery)
  const filterCategory: Ref<string> = ref(defaults.filterCategory)
  const filterCity: Ref<string> = ref(defaults.filterCity)
  const filterWebsite: Ref<ProspectWebsiteFilter> = ref(defaults.filterWebsite)
  const filterTemperature: Ref<TemperatureFilter> = ref(defaults.filterTemperature)
  const filterEmail: Ref<EmailFilter> = ref(defaults.filterEmail)
  const activeTab: Ref<'not_contacted' | 'contacted'> = ref(defaults.activeTab)

  /**
   * Restore filters from localStorage (client only).
   */
  function loadFilters(): void {
    if (import.meta.server) return
    const raw: string | null = localStorage.getItem(MY_PROSPECTS_FILTERS_STORAGE_KEY)
    if (!raw) return
    const parsed: MyProspectsFiltersState | null = parseStoredFilters(raw)
    if (!parsed) return
    searchQuery.value = parsed.searchQuery
    filterCategory.value = parsed.filterCategory
    filterCity.value = parsed.filterCity
    filterWebsite.value = parsed.filterWebsite
    filterTemperature.value = parsed.filterTemperature
    filterEmail.value = parsed.filterEmail
    activeTab.value = parsed.activeTab
  }

  /**
   * Persist the current filter snapshot to localStorage.
   */
  function saveFilters(): void {
    if (import.meta.server) return
    const snapshot: MyProspectsFiltersState = {
      searchQuery: searchQuery.value,
      filterCategory: filterCategory.value,
      filterCity: filterCity.value,
      filterWebsite: filterWebsite.value,
      filterTemperature: filterTemperature.value,
      filterEmail: filterEmail.value,
      activeTab: activeTab.value,
    }
    localStorage.setItem(MY_PROSPECTS_FILTERS_STORAGE_KEY, JSON.stringify(snapshot))
  }

  /**
   * Reset narrowing filters to their defaults (tab is kept).
   */
  function clearFilters(): void {
    const next: MyProspectsFiltersState = defaultFilters()
    searchQuery.value = next.searchQuery
    filterCategory.value = next.filterCategory
    filterCity.value = next.filterCity
    filterWebsite.value = next.filterWebsite
    filterTemperature.value = next.filterTemperature
    filterEmail.value = next.filterEmail
  }

  onMounted((): void => {
    loadFilters()
  })

  watch(
    [searchQuery, filterCategory, filterCity, filterWebsite, filterTemperature, filterEmail, activeTab],
    (): void => {
      saveFilters()
    },
  )

  return {
    searchQuery,
    filterCategory,
    filterCity,
    filterWebsite,
    filterTemperature,
    filterEmail,
    activeTab,
    clearFilters,
  }
}
