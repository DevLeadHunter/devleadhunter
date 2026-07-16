<template>
  <div class="space-y-5">
    <!-- Header: title + scope + filters -->
    <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <h1 class="text-xl font-semibold text-[var(--app-ink)]">Carte de prospection</h1>
        <p class="text-muted mt-1 max-w-2xl text-sm leading-relaxed">
          Cliquez une ville ou une région : zone couverte → ses prospects, zone vierge → nouvelle recherche.
        </p>
      </div>

      <div class="flex shrink-0 flex-wrap items-center gap-2">
        <!-- Scope (organization only) -->
        <select
          v-if="members.length > 0"
          v-model="store.scope"
          class="input-field h-9 w-full text-xs sm:w-48"
          :disabled="store.isLoading"
          @change="onScopeChange"
        >
          <option value="me">Mes prospects</option>
          <option value="org">Toute l'organisation</option>
          <option v-for="member in members" :key="member.user_id" :value="`member:${member.user_id}`">
            {{ member.name }}
          </option>
        </select>

        <!-- Filters drawer trigger -->
        <button type="button" class="btn-secondary relative h-9 text-xs" @click="openFiltersDrawer">
          <UIcon name="i-lucide-sliders-horizontal" class="mr-1.5 h-3.5 w-3.5" />
          Filtrer
          <span
            v-if="store.selectedCategories.length > 0"
            class="ml-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--app-ink)] px-1 text-[10px] font-semibold text-[var(--app-bg)]"
          >
            {{ store.selectedCategories.length }}
          </span>
        </button>
      </div>
    </div>

    <!-- Active trade pills (quick removal without opening the drawer) -->
    <div v-if="store.selectedCategories.length > 0" class="flex flex-wrap items-center gap-1.5">
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
      <button
        type="button"
        class="text-muted cursor-pointer text-xs underline underline-offset-2"
        @click="store.selectAllCategories()"
      >
        Tout afficher
      </button>
    </div>

    <!-- Counters + map, directly on the page -->
    <DashboardCoverageMap />
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import { computed, onMounted } from 'vue'
import type { CoverageMember } from '~/services/dashboardService'
import { useCoverageStore } from '~/stores/coverage'
import { useDrawerStackStore } from '~/stores/drawerStack'

/**
 * Dedicated prospection-coverage page. The map IS the interface: clicking a
 * covered zone lists its prospects, clicking a virgin zone starts a prefilled
 * search. Trade filters + attack suggestions live in the filters drawer.
 */
definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

useSeoMeta({ title: 'Carte de prospection — DevLeadHunter' })

const store = useCoverageStore()
const drawerStack = useDrawerStackStore()

/** Organization members selectable as scopes. */
const members: ComputedRef<CoverageMember[]> = computed((): CoverageMember[] => store.coverage?.members ?? [])

/** Open the filters & zones drawer. */
function openFiltersDrawer(): void {
  drawerStack.push({ kind: 'coverage-filters' })
}

/** Reload coverage when the scope changes. */
function onScopeChange(): void {
  void store.load()
}

onMounted((): void => {
  void store.load()
})
</script>
