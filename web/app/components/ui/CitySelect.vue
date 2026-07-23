<template>
  <div ref="rootEl" class="relative w-full">
    <input
      v-model="modelValue"
      type="text"
      role="combobox"
      autocomplete="off"
      aria-autocomplete="list"
      :aria-expanded="open"
      :placeholder="props.placeholder"
      class="input-field hover:border-[var(--app-ink)]"
      @focus="open = items.length > 0"
      @keydown="onKeydown"
    />
    <ul
      v-if="open && items.length > 0"
      class="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] py-1 shadow-lg"
      role="listbox"
    >
      <li
        v-for="(city, index) in items"
        :key="city"
        role="option"
        :aria-selected="index === highlighted"
        :class="[
          'cursor-pointer px-3 py-2 text-sm text-[var(--app-ink)]',
          index === highlighted ? 'bg-[var(--app-surface-2)]' : 'hover:bg-[var(--app-surface-2)]/60',
        ]"
        @mousedown.prevent="select(city)"
      >
        {{ city }}
      </li>
    </ul>
  </div>
</template>

<script lang="ts" setup>
import type { Commune, UiCitySelectProps } from '~/types/UiCitySelect'
import type { Ref } from 'vue'
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'

/** French city picker with geo.api.gouv.fr autosuggest; v-model is the field text. */
const modelValue = defineModel<string>({ required: true })

/** Placeholder shown while the field is empty. */
const props: UiCitySelectProps = defineProps({
  placeholder: {
    type: String,
    default: 'Rechercher une ville…',
  },
})

const items: Ref<string[]> = ref([])
const open: Ref<boolean> = ref(false)
const highlighted: Ref<number> = ref(-1)
const rootEl: Ref<HTMLElement | null> = ref(null)
let debounceId: ReturnType<typeof setTimeout> | null = null
let justSelected: boolean = false

/**
 * Fetch matching French communes for a search term (sorted by population).
 * @param term - The trimmed search term.
 * @returns A promise that resolves once ``items`` (and ``open``) are updated.
 */
async function searchCities(term: string): Promise<void> {
  try {
    const communes: Commune[] = await $fetch<Commune[]>('https://geo.api.gouv.fr/communes', {
      params: { nom: term, fields: 'nom', boost: 'population', limit: 10 },
    })
    // Dedupe homonymous communes by name (e.g. several "Marseillan").
    items.value = Array.from(new Set(communes.map((c: Commune): string => c.nom)))
    open.value = items.value.length > 0
  } catch {
    items.value = []
    open.value = false
  }
}

/**
 * Pick a suggestion: fill the field and close the dropdown.
 * @param city - The selected city name.
 */
function select(city: string): void {
  justSelected = true
  modelValue.value = city
  open.value = false
  items.value = []
  highlighted.value = -1
}

/**
 * Keyboard navigation within the suggestion list.
 * @param event - The keydown event from the input.
 */
function onKeydown(event: KeyboardEvent): void {
  if (!open.value || items.value.length === 0) return
  if (event.key === 'ArrowDown') {
    highlighted.value = (highlighted.value + 1) % items.value.length
    event.preventDefault()
  } else if (event.key === 'ArrowUp') {
    highlighted.value = (highlighted.value - 1 + items.value.length) % items.value.length
    event.preventDefault()
  } else if (event.key === 'Enter') {
    const city: string | undefined = items.value[highlighted.value]
    if (city) {
      select(city)
      event.preventDefault()
    }
  } else if (event.key === 'Escape') {
    open.value = false
  }
}

/** Close the dropdown when clicking outside the component. */
function onClickOutside(event: MouseEvent): void {
  if (rootEl.value && !rootEl.value.contains(event.target as Node)) open.value = false
}

// Typing drives the (debounced) search; erasing leaves an empty model (resets the filter).
watch(modelValue, (term: string): void => {
  if (justSelected) {
    justSelected = false
    return
  }
  highlighted.value = -1
  if (debounceId) clearTimeout(debounceId)
  const query: string = (term || '').trim()
  if (query.length < 2) {
    items.value = []
    open.value = false
    return
  }
  debounceId = setTimeout((): void => {
    void searchCities(query)
  }, 250)
})

onMounted((): void => document.addEventListener('click', onClickOutside))
onBeforeUnmount((): void => document.removeEventListener('click', onClickOutside))
</script>
