<template>
  <div class="relative w-full">
    <UIcon
      v-if="showIcon"
      name="i-lucide-map-pin"
      class="pointer-events-none absolute top-1/2 left-3 z-10 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
    />
    <input
      :id="inputId"
      :value="modelValue"
      type="text"
      :placeholder="placeholder"
      :required="required"
      autocomplete="off"
      role="combobox"
      :aria-expanded="isOpen"
      :class="['input-field', showIcon && 'pl-9']"
      @input="handleInput"
      @focus="handleFocus"
      @blur="handleBlur"
      @keydown="handleKeydown"
    />

    <ul
      v-if="isOpen"
      class="absolute z-50 mt-1 max-h-60 w-full overflow-y-auto rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] shadow-lg"
    >
      <li v-if="isSearching" class="flex items-center gap-2 px-3 py-2 text-sm text-[var(--app-ink-soft)]">
        <UIcon name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
        Recherche…
      </li>
      <li v-else-if="suggestions.length === 0" class="px-3 py-2 text-sm text-[var(--app-ink-soft)]">
        Aucune ville trouvée
      </li>
      <template v-else>
        <li
          v-for="(suggestion, index) in suggestions"
          :key="suggestion.code"
          :class="[
            'flex cursor-pointer items-baseline justify-between gap-3 px-3 py-2 text-sm text-[var(--app-ink)]',
            index === activeIndex ? 'bg-[var(--app-surface-2)]' : 'hover:bg-[var(--app-surface-2)]',
          ]"
          @mousedown.prevent="selectSuggestion(suggestion)"
          @mousemove="activeIndex = index"
        >
          <span class="font-medium">{{ suggestion.nom }}</span>
          <span v-if="suggestion.codeDepartement" class="text-xs text-[var(--app-ink-soft)]">
            {{ suggestion.codeDepartement }}
          </span>
        </li>
      </template>
    </ul>
  </div>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import { ref } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import type { CityAutocompleteInputProps, CitySuggestion } from '~/types/CityAutocompleteInput'

const minQueryLength: number = 2
const debounceDelayMs: number = 300
const maxResults: number = 6
const blurCloseDelayMs: number = 150

/** City autocomplete backed by geo.api.gouv.fr. */
const props: CityAutocompleteInputProps = defineProps({
  modelValue: {
    type: String,
    required: true,
  },
  placeholder: {
    type: String,
    default: 'Paris, Lyon, Rennes…',
  },
  inputId: {
    type: String,
    default: undefined,
  },
  required: {
    type: Boolean,
    default: false,
  },
  showIcon: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  select: [suggestion: CitySuggestion]
}>()

const suggestions: Ref<CitySuggestion[]> = ref([])
const isSearching: Ref<boolean> = ref(false)
const isOpen: Ref<boolean> = ref(false)
const activeIndex: Ref<number> = ref(-1)
let searchRequestId: number = 0
let blurTimeoutId: ReturnType<typeof setTimeout> | null = null

/**
 * Recherche les communes françaises correspondant à la saisie via geo.api.gouv.fr
 * (API publique, sans clé), triées par population.
 * @param query - Début du nom de ville saisi.
 * @returns Une promesse résolue une fois les suggestions mises à jour.
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
    const results: CitySuggestion[] = await $fetch<CitySuggestion[]>('https://geo.api.gouv.fr/communes', {
      query: {
        nom: trimmedQuery,
        fields: 'nom,codesPostaux,codeDepartement',
        boost: 'population',
        limit: maxResults,
      },
    })
    if (requestId !== searchRequestId) {
      return
    }
    suggestions.value = results
  } catch {
    if (requestId !== searchRequestId) {
      return
    }
    suggestions.value = []
  } finally {
    if (requestId === searchRequestId) {
      isSearching.value = false
      activeIndex.value = -1
    }
  }
}, debounceDelayMs)

/**
 * Propage la saisie au v-model et déclenche la recherche de suggestions.
 * @param event - Événement input natif.
 */
function handleInput(event: Event): void {
  const value: string = (event.target as HTMLInputElement).value
  emit('update:modelValue', value)
  if (value.trim().length >= minQueryLength) {
    isSearching.value = true
    isOpen.value = true
  } else {
    suggestions.value = []
    isSearching.value = false
    isOpen.value = false
  }
  void fetchSuggestions(value)
}

/**
 * Rouvre la liste de suggestions quand le champ reprend le focus.
 */
function handleFocus(): void {
  if (blurTimeoutId !== null) {
    clearTimeout(blurTimeoutId)
    blurTimeoutId = null
  }
  if (props.modelValue.trim().length >= minQueryLength && suggestions.value.length > 0) {
    isOpen.value = true
  }
}

/**
 * Ferme la liste après un court délai pour laisser le clic sur une suggestion aboutir.
 */
function handleBlur(): void {
  blurTimeoutId = setTimeout((): void => {
    isOpen.value = false
    blurTimeoutId = null
  }, blurCloseDelayMs)
}

/**
 * Navigation clavier dans la liste : flèches pour se déplacer, Entrée pour
 * sélectionner, Échap pour fermer.
 * @param event - Événement clavier natif.
 */
function handleKeydown(event: KeyboardEvent): void {
  if (!isOpen.value || suggestions.value.length === 0) {
    return
  }
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    activeIndex.value = (activeIndex.value + 1) % suggestions.value.length
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    activeIndex.value = activeIndex.value <= 0 ? suggestions.value.length - 1 : activeIndex.value - 1
  } else if (event.key === 'Enter' && activeIndex.value >= 0) {
    event.preventDefault()
    const suggestion: CitySuggestion | undefined = suggestions.value[activeIndex.value]
    if (suggestion) {
      selectSuggestion(suggestion)
    }
  } else if (event.key === 'Escape') {
    isOpen.value = false
  }
}

/**
 * Applique la ville sélectionnée dans la liste.
 * @param suggestion - Commune choisie.
 */
function selectSuggestion(suggestion: CitySuggestion): void {
  emit('update:modelValue', suggestion.nom)
  emit('select', suggestion)
  isOpen.value = false
  activeIndex.value = -1
}
</script>
