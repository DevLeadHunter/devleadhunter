<template>
  <div class="relative w-full">
    <input
      v-model="searchTerm"
      type="text"
      class="input-field"
      placeholder="Rechercher une entreprise…"
      autocomplete="off"
      role="combobox"
      :aria-expanded="isOpen"
      @focus="handleFocus"
      @blur="handleBlur"
    />

    <ul
      v-if="isOpen"
      class="absolute z-50 mt-1 max-h-60 w-full overflow-y-auto rounded-lg border border-[#30363d] bg-[#1a1a1a] shadow-lg"
    >
      <li v-if="isSearching" class="px-3 py-2 text-sm text-[#8b949e]">Recherche en cours…</li>
      <li v-else-if="searchTerm.trim().length < minQueryLength" class="px-3 py-2 text-sm text-[#8b949e]">
        Saisissez au moins {{ minQueryLength }} caractères
      </li>
      <li v-else-if="suggestions.length === 0" class="px-3 py-2 text-sm text-[#8b949e]">Aucune entreprise trouvée</li>
      <template v-else>
        <li
          v-for="suggestion in suggestions"
          :key="suggestion.id"
          class="cursor-pointer px-3 py-2 text-sm text-[#f9f9f9] hover:bg-[#30363d]"
          @mousedown.prevent="selectSuggestion(suggestion)"
        >
          <div class="font-medium">{{ suggestion.label }}</div>
          <p v-if="suggestion.description" class="mt-0.5 text-xs text-[#8b949e]">
            {{ suggestion.description }}
          </p>
        </li>
      </template>
    </ul>
  </div>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import { ref, watch } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import type { BusinessSearchInputExpose, BusinessSearchInputProps } from '~/types/BusinessSearchInput'
import type { ProspectSearchSuggestion } from '~/types'
import { searchProspectSuggestions } from '~/services/prospectsService'

const minQueryLength: number = 3
const debounceDelayMs: number = 500
const maxResults: number = 8
const blurCloseDelayMs: number = 150

/**
 * Définit les props du composant BusinessSearchInput.
 */
const props: BusinessSearchInputProps = defineProps({
  city: {
    type: String,
    default: undefined,
  },
})

const emit = defineEmits<{
  (e: 'select', suggestion: ProspectSearchSuggestion): void
}>()

const searchTerm: Ref<string> = ref<string>('')
const suggestions: Ref<ProspectSearchSuggestion[]> = ref<ProspectSearchSuggestion[]>([])
const isSearching: Ref<boolean> = ref<boolean>(false)
const isOpen: Ref<boolean> = ref<boolean>(false)
let searchRequestId: number = 0
let blurTimeoutId: ReturnType<typeof setTimeout> | null = null

/**
 * Lance une recherche de suggestions Google Maps pour la requête saisie.
 * @param query - Texte saisi par l'utilisateur.
 * @returns Une promesse résolue une fois la recherche terminée ou annulée.
 */
const fetchSuggestions = useDebounceFn(async (query: string): Promise<void> => {
  const trimmedQuery: string = query.trim()
  if (trimmedQuery.length < minQueryLength) {
    suggestions.value = []
    isOpen.value = false
    return
  }

  const requestId: number = ++searchRequestId
  isSearching.value = true
  isOpen.value = true

  try {
    const results: ProspectSearchSuggestion[] = await searchProspectSuggestions({
      query: trimmedQuery,
      city: props.city?.trim() || undefined,
      max_results: maxResults,
    })
    if (requestId !== searchRequestId) {
      return
    }
    suggestions.value = results
    isOpen.value = true
  } catch {
    if (requestId !== searchRequestId) {
      return
    }
    suggestions.value = []
    isOpen.value = true
  } finally {
    if (requestId === searchRequestId) {
      isSearching.value = false
    }
  }
}, debounceDelayMs)

watch(searchTerm, (value: string): void => {
  const trimmedQuery: string = value.trim()
  if (trimmedQuery.length >= minQueryLength) {
    isSearching.value = true
    isOpen.value = true
  } else {
    suggestions.value = []
    isSearching.value = false
    isOpen.value = false
  }
  void fetchSuggestions(value)
})

watch(
  (): string | undefined => props.city,
  (): void => {
    if (searchTerm.value.trim().length >= minQueryLength) {
      void fetchSuggestions(searchTerm.value)
    }
  },
)

/**
 * Ouvre la liste de suggestions quand le champ reçoit le focus.
 */
function handleFocus(): void {
  if (blurTimeoutId !== null) {
    clearTimeout(blurTimeoutId)
    blurTimeoutId = null
  }
  if (searchTerm.value.trim().length >= minQueryLength) {
    isOpen.value = true
  }
}

/**
 * Ferme la liste après un court délai pour laisser le clic sur une suggestion se produire.
 */
function handleBlur(): void {
  blurTimeoutId = setTimeout((): void => {
    isOpen.value = false
    blurTimeoutId = null
  }, blurCloseDelayMs)
}

/**
 * Applique une suggestion sélectionnée dans la liste.
 * @param suggestion - Entreprise sélectionnée.
 */
function selectSuggestion(suggestion: ProspectSearchSuggestion): void {
  searchTerm.value = suggestion.label
  isOpen.value = false
  emit('select', suggestion)
}

/**
 * Réinitialise le champ de recherche et l'état interne du composant.
 */
function reset(): void {
  searchRequestId += 1
  searchTerm.value = ''
  suggestions.value = []
  isOpen.value = false
  isSearching.value = false
}

defineExpose<BusinessSearchInputExpose>({ reset })
</script>
