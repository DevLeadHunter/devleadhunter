<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 class="text-xl font-semibold text-[var(--app-ink)]">Carte de prospection</h1>
        <p class="text-muted mt-1 max-w-2xl text-sm leading-relaxed">
          Votre territoire, métier par métier : ce qui est couvert, ce qui reste à conquérir.
        </p>
      </div>
    </div>

    <!-- Trade filter chips -->
    <div v-if="availableCategories.length > 0" class="flex flex-wrap items-center gap-2">
      <span class="text-muted text-[11px] tracking-wide uppercase">Métiers</span>
      <button
        type="button"
        class="cursor-pointer rounded-full border px-3 py-1 text-xs font-medium transition-colors"
        :class="
          selectedCategories.length === 0
            ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-bg)]'
            : 'border-[var(--app-line)] bg-[var(--app-surface)] text-[var(--app-ink-soft)] hover:border-[var(--app-ink-soft)]'
        "
        @click="selectAllCategories"
      >
        Tous les métiers
      </button>
      <button
        v-for="category in availableCategories"
        :key="category"
        type="button"
        class="cursor-pointer rounded-full border px-3 py-1 text-xs font-medium transition-colors"
        :class="
          selectedCategories.includes(category)
            ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-bg)]'
            : 'border-[var(--app-line)] bg-[var(--app-surface)] text-[var(--app-ink-soft)] hover:border-[var(--app-ink-soft)]'
        "
        @click="toggleCategory(category)"
      >
        {{ category }}
      </button>
    </div>

    <!-- Map + conquest panel -->
    <div class="grid gap-6 xl:grid-cols-[1fr_320px]">
      <div class="app-card p-4 sm:p-5">
        <DashboardCoverageMap variant="full" :categories="selectedCategories" @loaded="onCoverageLoaded" />
      </div>

      <!-- À conquérir -->
      <aside class="space-y-5">
        <div class="app-card p-4 sm:p-5">
          <h2 class="flex items-center gap-2 text-sm font-semibold text-[var(--app-ink)]">
            <UIcon name="i-lucide-flag" class="h-4 w-4 text-[var(--app-accent)]" />
            Régions à conquérir
          </h2>
          <p v-if="uncoveredRegions.length === 0 && hasLoaded" class="text-muted mt-3 text-sm">
            Toutes les régions sont couvertes — beau travail. 🎉
          </p>
          <ul v-else class="mt-3 flex flex-wrap gap-1.5">
            <li
              v-for="region in uncoveredRegions"
              :key="region"
              class="rounded-full border border-dashed border-[var(--app-line)] px-2.5 py-1 text-xs text-[var(--app-ink-soft)]"
            >
              {{ region }}
            </li>
          </ul>
        </div>

        <div class="app-card p-4 sm:p-5">
          <h2 class="flex items-center gap-2 text-sm font-semibold text-[var(--app-ink)]">
            <UIcon name="i-lucide-crosshair" class="h-4 w-4 text-[var(--app-accent)]" />
            Villes à attaquer
          </h2>
          <p class="text-muted mt-1 text-xs leading-relaxed">
            Grandes villes jamais prospectées{{ selectedCategories.length > 0 ? ' pour ces métiers' : '' }}.
          </p>
          <p v-if="suggestedCities.length === 0 && hasLoaded" class="text-muted mt-3 text-sm">
            Toutes les grandes villes sont déjà prospectées. 💪
          </p>
          <ul v-else class="mt-2 divide-y divide-[var(--app-line-soft)]">
            <li v-for="city in suggestedCities" :key="city.name" class="flex items-center justify-between gap-2 py-2">
              <div class="min-w-0">
                <p class="truncate text-sm text-[var(--app-ink)]">{{ city.name }}</p>
                <p class="text-muted text-[11px]">{{ regionName(city.region) }}</p>
              </div>
              <button type="button" class="btn-secondary shrink-0 !px-2.5 !py-1 text-xs" @click="prospectCity(city)">
                Prospecter
              </button>
            </li>
          </ul>
        </div>
      </aside>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'
import { lookupCity } from '~/composables/useFranceGeo'
import { useDrawerStackStore } from '~/stores/drawerStack'
import type { DashboardCoverageMapLoadedPayload } from '~/types/DashboardCoverageMap'
import type { FranceMajorCity } from '~/utils/franceTerritory'
import { FRANCE_MAJOR_CITIES, FRANCE_REGIONS } from '~/utils/franceTerritory'

/**
 * Dedicated prospection-coverage page: the full-size map with a trade filter,
 * plus a « conquest » panel (uncovered regions + major cities never prospected)
 * that turns every gap into a one-click search.
 */
definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

useSeoMeta({ title: 'Carte de prospection — DevLeadHunter' })

const drawerStack = useDrawerStackStore()

/** Selected trades — empty means « all trades » (no filter). */
const selectedCategories: Ref<string[]> = ref<string[]>([])

/** Trades available in the current scope (from the last coverage load). */
const availableCategories: Ref<string[]> = ref<string[]>([])

/** Last coverage payload emitted by the map (feeds the conquest panel). */
const lastPayload: Ref<DashboardCoverageMapLoadedPayload | null> = ref<DashboardCoverageMapLoadedPayload | null>(null)

/** True once the first coverage load happened (gates the « all done » states). */
const hasLoaded: Ref<boolean> = ref<boolean>(false)

/** INSEE region codes covered by at least one prospected city. */
const coveredRegionCodes: ComputedRef<Set<string>> = computed((): Set<string> => {
  const covered = new Set<string>()
  const payload: DashboardCoverageMapLoadedPayload | null = lastPayload.value
  if (!payload) return covered
  for (const city of payload.coverage.cities) {
    const geo = lookupCity(payload.cityGeo, city.city)
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

/** Prospected city names, normalised for matching against the suggestions. */
const coveredCityNames: ComputedRef<Set<string>> = computed((): Set<string> => {
  const names = new Set<string>()
  for (const city of lastPayload.value?.coverage.cities ?? []) {
    names.add(normalizeCityName(city.city))
  }
  return names
})

/** Major cities never prospected (biggest first), capped for the panel. */
const suggestedCities: ComputedRef<FranceMajorCity[]> = computed((): FranceMajorCity[] =>
  FRANCE_MAJOR_CITIES.filter((city): boolean => !coveredCityNames.value.has(normalizeCityName(city.name))).slice(0, 10),
)

/**
 * Normalise a city name for comparison (lowercase, accent-free, trimmed).
 * @param name - Raw city name.
 * @returns The comparable key.
 */
function normalizeCityName(name: string): string {
  return name.trim().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
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
 * Store the coverage payload emitted by the map (side panels recompute from it).
 * @param payload - Coverage + geocoding results for the current filters.
 */
function onCoverageLoaded(payload: DashboardCoverageMapLoadedPayload): void {
  lastPayload.value = payload
  hasLoaded.value = true
  if (payload.coverage.available_categories.length > 0) {
    availableCategories.value = payload.coverage.available_categories
  }
}

/** Reset the trade filter to « all trades ». */
function selectAllCategories(): void {
  selectedCategories.value = []
}

/**
 * Toggle one trade in the filter (empty selection = all trades).
 * @param category - Trade to toggle.
 */
function toggleCategory(category: string): void {
  const current: string[] = selectedCategories.value
  selectedCategories.value = current.includes(category)
    ? current.filter((c: string): boolean => c !== category)
    : [...current, category]
}

/**
 * Open the prospect-search drawer prefilled with a suggested city (and the
 * trade when exactly one is selected) — the « gap → attack » shortcut.
 * @param city - Suggested city to prospect.
 */
function prospectCity(city: FranceMajorCity): void {
  drawerStack.push({
    kind: 'search-prospects',
    prefill: {
      city: city.name,
      ...(selectedCategories.value.length === 1 ? { category: selectedCategories.value[0] as string } : {}),
    },
  })
}
</script>
