<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[460px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl"
      >
        <!-- Header -->
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Revenir au volet précédent"
            @click="emit('back')"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>
          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)]"
          >
            <UIcon name="i-lucide-sliders-horizontal" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </span>
          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">Filtres & zones</h2>
            <p class="mt-0.5 text-[11px] text-[var(--app-ink-soft)]">Métiers affichés + prochaines villes à attaquer</p>
          </div>
          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <!-- Body -->
        <div class="flex-1 space-y-6 overflow-y-auto px-5 py-4">
          <!-- Trades: search bar with suggestions + selected pills -->
          <section>
            <label for="coverage-trade-search" class="app-label mb-1.5 block">Métiers</label>
            <div class="relative">
              <UIcon
                name="i-lucide-search"
                class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
              />
              <input
                id="coverage-trade-search"
                v-model="tradeQuery"
                type="text"
                placeholder="Rechercher un métier (plombier, électricien…)"
                class="app-input w-full pl-9"
                autocomplete="off"
                @keydown.enter.prevent="pickFirstSuggestion"
                @keydown.escape="tradeQuery = ''"
              />
              <!-- Suggestions -->
              <ul
                v-if="tradeSuggestions.length > 0"
                class="absolute z-10 mt-1 w-full overflow-hidden rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] shadow-lg"
              >
                <li v-for="suggestion in tradeSuggestions" :key="suggestion">
                  <button
                    type="button"
                    class="flex w-full cursor-pointer items-center justify-between px-3 py-2 text-left text-sm text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
                    @click="pickSuggestion(suggestion)"
                  >
                    {{ suggestion }}
                    <UIcon name="i-lucide-plus" class="h-3.5 w-3.5 text-[var(--app-faint)]" />
                  </button>
                </li>
              </ul>
            </div>

            <!-- Selected pills -->
            <div class="mt-2.5 flex flex-wrap items-center gap-1.5">
              <button
                type="button"
                class="cursor-pointer rounded-full border px-2.5 py-1 text-xs font-medium transition-colors"
                :class="
                  store.selectedCategories.length === 0
                    ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-bg)]'
                    : 'border-[var(--app-line)] text-[var(--app-ink-soft)] hover:border-[var(--app-ink-soft)]'
                "
                @click="store.selectAllCategories()"
              >
                Tous les métiers
              </button>
              <span
                v-for="category in store.selectedCategories"
                :key="category"
                class="inline-flex items-center gap-1 rounded-full border border-[var(--app-ink)] bg-[var(--app-ink)] py-1 pr-1.5 pl-2.5 text-xs font-medium text-[var(--app-bg)]"
              >
                {{ category }}
                <button
                  type="button"
                  class="flex h-4 w-4 cursor-pointer items-center justify-center rounded-full transition-colors hover:bg-[var(--app-bg)]/20"
                  :aria-label="`Retirer ${category}`"
                  @click="store.toggleCategory(category)"
                >
                  <UIcon name="i-lucide-x" class="h-3 w-3" />
                </button>
              </span>
            </div>
          </section>

          <!-- Cities to attack -->
          <section>
            <h3 class="app-label mb-1 flex items-center gap-1.5">
              <UIcon name="i-lucide-crosshair" class="h-3.5 w-3.5 text-[var(--app-accent)]" />
              Villes à attaquer
            </h3>
            <p class="text-muted mb-1 text-[11px] leading-relaxed">
              Grandes villes jamais prospectées{{ store.selectedCategories.length > 0 ? ' pour ces métiers' : '' }}.
            </p>
            <p v-if="store.suggestedCities.length === 0 && store.hasLoaded" class="text-muted py-2 text-sm">
              Toutes les grandes villes sont déjà prospectées. 💪
            </p>
            <ul v-else class="divide-y divide-[var(--app-line-soft)]">
              <li
                v-for="city in store.suggestedCities"
                :key="city.name"
                class="flex items-center justify-between gap-2 py-2"
              >
                <div class="min-w-0">
                  <p class="truncate text-sm text-[var(--app-ink)]">{{ city.name }}</p>
                  <p class="text-muted text-[11px]">{{ regionName(city.region) }}</p>
                </div>
                <button
                  type="button"
                  class="btn-secondary shrink-0 !px-2.5 !py-1 text-xs"
                  @click="prospectCity(city.name)"
                >
                  Prospecter
                </button>
              </li>
            </ul>
          </section>

          <!-- Uncovered regions (info only) -->
          <section>
            <h3 class="app-label mb-1.5 flex items-center gap-1.5">
              <UIcon name="i-lucide-flag" class="h-3.5 w-3.5 text-[var(--app-accent)]" />
              Régions à conquérir
            </h3>
            <p v-if="store.uncoveredRegions.length === 0 && store.hasLoaded" class="text-muted text-sm">
              Toutes les régions sont couvertes — beau travail. 🎉
            </p>
            <div v-else class="flex flex-wrap gap-1.5">
              <span
                v-for="region in store.uncoveredRegions"
                :key="region"
                class="rounded-full border border-dashed border-[var(--app-line)] px-2.5 py-1 text-xs text-[var(--app-ink-soft)]"
              >
                {{ region }}
              </span>
            </div>
          </section>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'
import { normalizeCityName, useCoverageStore } from '~/stores/coverage'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { FRANCE_REGIONS } from '~/utils/franceTerritory'

/**
 * Coverage-map filters drawer: trade search bar with suggestions (scales to
 * many trades), the selected trades as removable pills, the « villes à
 * attaquer » shortcuts and the uncovered regions as plain info.
 */
defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits<{
  /** Close every drawer. */
  close: []
  /** Go back to the previous drawer of the stack. */
  back: []
}>()

const store = useCoverageStore()
const drawerStack = useDrawerStackStore()

/** Trade search query. */
const tradeQuery: Ref<string> = ref('')

/** Suggestions: available trades matching the query, not yet selected. */
const tradeSuggestions: ComputedRef<string[]> = computed((): string[] => {
  const query: string = normalizeCityName(tradeQuery.value)
  if (!query) return []
  return store.availableCategories
    .filter(
      (category: string): boolean =>
        normalizeCityName(category).includes(query) && !store.selectedCategories.includes(category),
    )
    .slice(0, 8)
})

/**
 * Add a suggested trade to the filter.
 * @param category - Trade picked from the suggestion list.
 */
function pickSuggestion(category: string): void {
  store.toggleCategory(category)
  tradeQuery.value = ''
}

/** Enter picks the first suggestion (keyboard-first flow). */
function pickFirstSuggestion(): void {
  const first: string | undefined = tradeSuggestions.value[0]
  if (first) pickSuggestion(first)
}

/**
 * Resolve a region display name from its INSEE code.
 * @param code - INSEE region code.
 * @returns The region name (or the raw code as fallback).
 */
function regionName(code: string): string {
  return FRANCE_REGIONS[code] ?? code
}

/**
 * Open the prospect-search drawer prefilled with a suggested city (stacked on
 * top of this drawer — back returns here).
 * @param city - City to prospect.
 */
function prospectCity(city: string): void {
  drawerStack.push({
    kind: 'search-prospects',
    prefill: {
      city,
      ...(store.selectedCategories.length === 1 ? { category: store.selectedCategories[0] as string } : {}),
    },
  })
}
</script>

<style scoped>
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
