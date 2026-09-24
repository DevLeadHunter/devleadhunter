import type { Ref } from 'vue'
import type { ProspectWebsiteFilter } from '~/types'
import type { DlhModuleKey } from '~/types/UiSidebar'
import { ref, watch, onMounted } from 'vue'
import { useModuleStore } from '~/stores/moduleStore'

/** localStorage key persisting the « Mes prospects » list filters (site module; others get a suffix). */
const MY_PROSPECTS_FILTERS_STORAGE_KEY: string = 'dlh-my-prospects-filters'

const WEBSITE_FILTER_VALUES: ProspectWebsiteFilter[] = ['all', 'yes', 'no', 'dead', 'improvable', 'chat', 'no-chat']

export type TemperatureFilter = 'all' | 'hot' | 'warm' | 'cold'
const TEMPERATURE_FILTER_VALUES: TemperatureFilter[] = ['all', 'hot', 'warm', 'cold']

export type EmailFilter = 'all' | 'undeliverable'
const EMAIL_FILTER_VALUES: EmailFilter[] = ['all', 'undeliverable']

export type ProspectSortOrder = 'recent' | 'demand'
const SORT_ORDER_VALUES: ProspectSortOrder[] = ['recent', 'demand']

/** Persisted filter state for the my-prospects page. */
export type MyProspectsFiltersState = {
  searchQuery: string
  filterCategory: string
  filterCity: string
  filterWebsite: ProspectWebsiteFilter
  filterTemperature: TemperatureFilter
  filterEmail: EmailFilter
  sortOrder: ProspectSortOrder
  activeTab: 'not_contacted' | 'contacted'
}

/**
 * Storage key of a module's filters: each module keeps its own, since the site module hunts
 * pros without a site while the Réceptionniste IA takes them with or without one.
 * @param moduleKey - Active dashboard module.
 * @returns The localStorage key for that module.
 */
function filtersStorageKey(moduleKey: DlhModuleKey): string {
  return moduleKey === 'websites'
    ? MY_PROSPECTS_FILTERS_STORAGE_KEY
    : `${MY_PROSPECTS_FILTERS_STORAGE_KEY}:${moduleKey}`
}

/**
 * Default filter state for the my-prospects page.
 * @param moduleKey - Active dashboard module.
 * @returns A fresh filter snapshot.
 */
function defaultFilters(moduleKey: DlhModuleKey): MyProspectsFiltersState {
  return {
    searchQuery: '',
    filterCategory: '',
    filterCity: '',
    filterWebsite: moduleKey === 'ai-assistant' ? 'all' : 'no',
    filterTemperature: 'all',
    filterEmail: 'all',
    sortOrder: moduleKey === 'ai-assistant' ? 'demand' : 'recent',
    activeTab: 'not_contacted',
  }
}

/**
 * Parse and validate a stored filter snapshot.
 * @param raw - JSON string from localStorage.
 * @param defaults - The active module's defaults, used for missing or invalid values.
 * @returns A validated state, or null when invalid.
 */
function parseStoredFilters(raw: string, defaults: MyProspectsFiltersState): MyProspectsFiltersState | null {
  try {
    const parsed: Partial<MyProspectsFiltersState> = JSON.parse(raw) as Partial<MyProspectsFiltersState>
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
    const sortOrder: ProspectSortOrder = SORT_ORDER_VALUES.includes(parsed.sortOrder as ProspectSortOrder)
      ? (parsed.sortOrder as ProspectSortOrder)
      : defaults.sortOrder

    return {
      searchQuery: typeof parsed.searchQuery === 'string' ? parsed.searchQuery : defaults.searchQuery,
      filterCategory: typeof parsed.filterCategory === 'string' ? parsed.filterCategory : defaults.filterCategory,
      filterCity: typeof parsed.filterCity === 'string' ? parsed.filterCity : defaults.filterCity,
      filterWebsite,
      filterTemperature,
      filterEmail,
      sortOrder,
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
  sortOrder: Ref<ProspectSortOrder>
  activeTab: Ref<'not_contacted' | 'contacted'>
  clearFilters: () => void
} {
  const moduleStore: ReturnType<typeof useModuleStore> = useModuleStore()
  const defaults: MyProspectsFiltersState = defaultFilters(moduleStore.activeKey)
  const searchQuery: Ref<string> = ref(defaults.searchQuery)
  const filterCategory: Ref<string> = ref(defaults.filterCategory)
  const filterCity: Ref<string> = ref(defaults.filterCity)
  const filterWebsite: Ref<ProspectWebsiteFilter> = ref(defaults.filterWebsite)
  const filterTemperature: Ref<TemperatureFilter> = ref(defaults.filterTemperature)
  const filterEmail: Ref<EmailFilter> = ref(defaults.filterEmail)
  const sortOrder: Ref<ProspectSortOrder> = ref(defaults.sortOrder)
  const activeTab: Ref<'not_contacted' | 'contacted'> = ref(defaults.activeTab)

  /**
   * Apply a full filter snapshot to the refs.
   * @param snapshot - The filters to show.
   */
  function applyFilters(snapshot: MyProspectsFiltersState): void {
    searchQuery.value = snapshot.searchQuery
    filterCategory.value = snapshot.filterCategory
    filterCity.value = snapshot.filterCity
    filterWebsite.value = snapshot.filterWebsite
    filterTemperature.value = snapshot.filterTemperature
    filterEmail.value = snapshot.filterEmail
    sortOrder.value = snapshot.sortOrder
    activeTab.value = snapshot.activeTab
  }

  /**
   * Restore the active module's filters from localStorage, or its defaults (client only).
   */
  function loadFilters(): void {
    if (import.meta.server) return
    const moduleDefaults: MyProspectsFiltersState = defaultFilters(moduleStore.activeKey)
    const raw: string | null = localStorage.getItem(filtersStorageKey(moduleStore.activeKey))
    const parsed: MyProspectsFiltersState | null = raw ? parseStoredFilters(raw, moduleDefaults) : null
    applyFilters(parsed ?? moduleDefaults)
  }

  /**
   * Persist the current filter snapshot under the active module's key.
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
      sortOrder: sortOrder.value,
      activeTab: activeTab.value,
    }
    localStorage.setItem(filtersStorageKey(moduleStore.activeKey), JSON.stringify(snapshot))
  }

  /**
   * Reset narrowing filters to the active module's defaults (tab is kept).
   */
  function clearFilters(): void {
    applyFilters({ ...defaultFilters(moduleStore.activeKey), sortOrder: sortOrder.value, activeTab: activeTab.value })
  }

  onMounted((): void => {
    loadFilters()
  })

  watch(
    [searchQuery, filterCategory, filterCity, filterWebsite, filterTemperature, filterEmail, sortOrder, activeTab],
    (): void => {
      saveFilters()
    },
  )

  // The module is restored from storage by the sidebar after mount, and can switch while
  // the page stays open: either way, show that module's own filters.
  watch(
    (): DlhModuleKey => moduleStore.activeKey,
    (): void => {
      loadFilters()
    },
  )

  return {
    searchQuery,
    filterCategory,
    filterCity,
    filterWebsite,
    filterTemperature,
    filterEmail,
    sortOrder,
    activeTab,
    clearFilters,
  }
}
