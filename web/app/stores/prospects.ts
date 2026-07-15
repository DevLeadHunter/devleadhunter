import { defineStore } from 'pinia'
import type { Prospect, ProspectSearchFilters } from '~/types'
import type { Ref } from 'vue'
import { ref, computed } from 'vue'
import { useUserStore } from './user'

/**
 * Pinia store for prospect management
 * @module stores/prospects
 */

/**
 * Prospects store definition
 */
export const useProspectsStore = defineStore('prospects', () => {
  // State
  const prospects: Ref<Prospect[]> = ref([])
  const currentProspect: Ref<Prospect | null> = ref(null)
  const isLoading: Ref<boolean> = ref(false)
  const error: Ref<string | null> = ref(null)
  const selectedProspects: Ref<string[]> = ref([])
  const searchFilters: Ref<ProspectSearchFilters> = ref({})
  const hasSearched: Ref<boolean> = ref(false)

  // Getters
  const prospectsCount = computed(() => prospects.value.length)

  const prospectsWithWebsite = computed(() => prospects.value.filter((p) => p.website && p.website !== ''))

  const prospectsWithoutWebsite = computed(() => prospects.value.filter((p) => !p.website || p.website === ''))

  const hasSelectedProspects = computed(() => selectedProspects.value.length > 0)

  /**
   * Search for prospects based on filters
   * @param {ProspectSearchFilters} filters - Search filters
   * @returns {Promise<void>} Promise that resolves when search is complete
   * @throws {Error} If search fails
   * @example
   * ```typescript
   * await prospectsStore.searchProspects({
   *   category: 'restaurant',
   *   city: 'Paris',
   *   maxResults: 50
   * });
   * ```
   */
  async function searchProspects(filters: ProspectSearchFilters): Promise<void> {
    try {
      isLoading.value = true
      error.value = null
      searchFilters.value = filters

      // Build request payload
      const requestBody: Record<string, string | number> = {
        max_results: filters.maxResults || 50,
      }

      if (filters.category && filters.category !== 'all') {
        requestBody.category = filters.category
      }

      if (filters.city) {
        requestBody.city = filters.city
      }

      if (filters.source && filters.source !== 'all') {
        requestBody.source = filters.source
      }

      // Call the real API
      const config = useRuntimeConfig()
      const userStore = useUserStore()

      const response = await $fetch<{
        total: number
        prospects: Prospect[]
        has_website: number
        without_website: number
      }>(`${config.public.apiBase}/api/v1/prospects/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(userStore.token && { Authorization: `Bearer ${userStore.token}` }),
        },
        body: requestBody,
      })

      prospects.value = response.prospects
      hasSearched.value = true

      // Refresh user credits after successful search
      try {
        await userStore.refreshUser()
      } catch (refreshErr) {
        console.error('Failed to refresh user credits after search:', refreshErr)
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Search failed'
      prospects.value = []
      hasSearched.value = true
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Get prospect by ID
   * @param {string} id - Prospect ID
   * @returns {Prospect | undefined} The prospect or undefined if not found
   */
  function getProspectById(id: string): Prospect | undefined {
    return prospects.value.find((p) => p.id === id)
  }

  /**
   * Toggle prospect selection
   * @param {string} prospectId - Prospect ID
   * @returns {void}
   */
  function toggleProspectSelection(prospectId: string): void {
    const index = selectedProspects.value.indexOf(prospectId)
    if (index > -1) {
      selectedProspects.value.splice(index, 1)
    } else {
      selectedProspects.value.push(prospectId)
    }
  }

  /**
   * Clear all selected prospects
   * @returns {void}
   */
  function clearSelection(): void {
    selectedProspects.value = []
  }

  /**
   * Get selected prospects data
   * @returns {Prospect[]} Array of selected prospects
   */
  function getSelectedProspects(): Prospect[] {
    return prospects.value.filter((p) => selectedProspects.value.includes(p.id))
  }

  return {
    // State
    prospects,
    currentProspect,
    isLoading,
    error,
    selectedProspects,
    searchFilters,
    hasSearched,
    // Getters
    prospectsCount,
    prospectsWithWebsite,
    prospectsWithoutWebsite,
    hasSelectedProspects,
    // Actions
    searchProspects,
    getProspectById,
    toggleProspectSelection,
    clearSelection,
    getSelectedProspects,
  }
})
