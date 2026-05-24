<template>
  <form @submit.prevent="handleSubmit">
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <!-- Category Select -->
      <div>
        <label for="category" class="text-muted mb-1.5 block text-xs font-medium"> Category </label>
        <select id="category" v-model="localFilters.category" class="input-field">
          <option value="all">All Categories</option>
          <option value="restaurant">Restaurant</option>
          <option value="plombier">Plombier</option>
          <option value="electricien">Electricien</option>
          <option value="coiffeur">Coiffeur</option>
          <option value="garage">Garage</option>
        </select>
      </div>

      <!-- City Input -->
      <div>
        <label for="city" class="text-muted mb-1.5 block text-xs font-medium"> City </label>
        <input
          id="city"
          v-model="localFilters.city"
          type="text"
          placeholder="e.g., Paris, Lyon, Marseille"
          class="input-field"
        />
      </div>

      <!-- Source Select -->
      <div>
        <label for="source" class="text-muted mb-1.5 block text-xs font-medium"> Source </label>
        <select id="source" v-model="localFilters.source" class="input-field">
          <option value="all">All Sources</option>
          <option value="google">Google</option>
          <option value="pagesjaunes">Pages Jaunes</option>
          <option value="yelp">Yelp</option>
          <option value="osm">OSM</option>
          <option value="mappy">Mappy</option>
        </select>
      </div>

      <!-- Max Results Input -->
      <div>
        <label for="maxResults" class="text-muted mb-1.5 block text-xs font-medium"> Max Results </label>
        <input
          id="maxResults"
          v-model.number="localFilters.maxResults"
          type="number"
          min="1"
          max="1000"
          placeholder="50"
          class="input-field"
        />
      </div>
    </div>

    <!-- Submit Button -->
    <div class="mt-4 flex justify-center sm:justify-end">
      <button type="submit" :disabled="isLoading" class="btn-primary w-full sm:w-auto">
        <span v-if="isLoading" class="flex items-center justify-center gap-2">
          <i class="fa-solid fa-spinner fa-spin"></i>
          Searching...
        </span>
        <span v-else class="flex items-center justify-center gap-1.5">
          <i class="fa-solid fa-magnifying-glass"></i>
          Search Prospects
        </span>
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
import type { ProspectSearchFilters } from '~/types'
import type { Ref } from 'vue'
import { ref, watch } from 'vue'
import { useProspectsStore } from '~/stores/prospects'
import { useToast } from '~/composables/useToast'

/**
 * Props for the SearchForm component
 */
interface Props {
  /**
   * Initial search filters
   */
  filters?: ProspectSearchFilters
}

/**
 * Props definition
 */
const props = defineProps<Props>()

/**
 * Prospects store instance
 */
const prospectsStore = useProspectsStore()

/**
 * Toast composable
 */
const toast = useToast()

/**
 * Local filters state
 */
const localFilters: Ref<ProspectSearchFilters> = ref({
  category: props.filters?.category || 'all',
  city: props.filters?.city || '',
  source: props.filters?.source || 'pagesjaunes',
  maxResults: props.filters?.maxResults || 5,
})

/**
 * Loading state
 */
const isLoading: Ref<boolean> = ref(false)

/**
 * Handle form submission
 * @returns {Promise<void>}
 */
const handleSubmit = async (): Promise<void> => {
  try {
    isLoading.value = true

    // Build filters object, excluding undefined values
    const filters: ProspectSearchFilters = {}

    if (localFilters.value.category && localFilters.value.category !== 'all') {
      filters.category = localFilters.value.category
    }

    if (localFilters.value.city) {
      filters.city = localFilters.value.city
    }

    if (localFilters.value.source && localFilters.value.source !== 'all') {
      filters.source = localFilters.value.source
    }

    if (localFilters.value.maxResults) {
      filters.maxResults = localFilters.value.maxResults
    }

    await prospectsStore.searchProspects(filters)

    if (prospectsStore.prospects.length > 0) {
      toast.success(`Found ${prospectsStore.prospects.length} prospects`)
    } else {
      toast.info('No prospects found matching your criteria')
    }
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Search failed')
  } finally {
    isLoading.value = false
  }
}

/**
 * Watch for props changes and update local filters
 */
watch(
  () => props.filters,
  (newFilters) => {
    if (newFilters) {
      localFilters.value = { ...newFilters }
    }
  },
  { deep: true },
)
</script>
