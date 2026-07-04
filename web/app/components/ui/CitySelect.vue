<template>
  <div ref="rootEl" class="relative w-full">
    <input
      v-model="modelValue"
      type="text"
      role="combobox"
      autocomplete="off"
      aria-autocomplete="list"
      :aria-expanded="open"
      :placeholder="placeholder"
      class="input-field hover:border-[#f9f9f9]"
      @focus="open = items.length > 0"
      @keydown="onKeydown"
    />
    <ul
      v-if="open && items.length > 0"
      class="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-[#30363d] bg-[#1a1a1a] py-1 shadow-lg"
      role="listbox"
    >
      <li
        v-for="(city, index) in items"
        :key="city"
        role="option"
        :aria-selected="index === highlighted"
        :class="[
          'cursor-pointer px-3 py-2 text-sm text-[#f9f9f9]',
          index === highlighted ? 'bg-[#30363d]' : 'hover:bg-[#30363d]/60',
        ]"
        @mousedown.prevent="select(city)"
      >
        {{ city }}
      </li>
    </ul>
  </div>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'

/**
 * Reusable French-city picker with type-to-search autosuggestion.
 *
 * A normal text input (same ``.input-field`` style as the rest of the app, with a
 * white border on hover) backed by a custom suggestion dropdown that queries the
 * official, free, key-less ``geo.api.gouv.fr`` communes API — so any real French
 * city is searchable. The ``v-model`` is the field text: picking a suggestion
 * fills it, erasing it resets the value (e.g. clears a filter). Reusable app-wide.
 */
const modelValue = defineModel<string>({ required: true })

/**
 * Defines the component props.
 */
defineProps({
  placeholder: {
    type: String,
    default: 'Rechercher une ville…',
  },
})

/** A French commune as returned by geo.api.gouv.fr (only the fields we request). */
interface Commune {
  nom: string
}

const items: Ref<string[]> = ref<string[]>([])
const open: Ref<boolean> = ref<boolean>(false)
const highlighted: Ref<number> = ref<number>(-1)
const rootEl: Ref<HTMLElement | null> = ref<HTMLElement | null>(null)
let debounceId: ReturnType<typeof setTimeout> | null = null
let justSelected = false

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
