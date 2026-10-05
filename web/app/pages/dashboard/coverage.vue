<template>
  <div class="flex min-h-full flex-col gap-5">
    <UiPageHeader eyebrow="Prospection" title="Carte de prospection">
      <template #description>
        Cliquez une ville ou une région : zone couverte
        <UIcon name="i-lucide-arrow-right" class="inline-block h-3.5 w-3.5 align-[-2px]" /> ses prospects, zone vierge
        <UIcon name="i-lucide-arrow-right" class="inline-block h-3.5 w-3.5 align-[-2px]" /> nouvelle recherche.
      </template>
      <template v-if="members.length > 0" #actions>
        <div class="w-full @2xl:w-56">
          <UiSelectField v-model="scope" :options="scopeOptions" :disabled="store.isLoading" />
        </div>
      </template>
      <template #primary-action>
        <button
          type="button"
          class="app-btn-primary relative h-11 px-4 text-sm whitespace-nowrap @2xl:pointer-fine:h-9 @2xl:pointer-fine:text-xs"
          @click="openFiltersDrawer"
        >
          <UIcon name="i-lucide-sliders-horizontal" class="h-3.5 w-3.5" />
          Filtrer
          <span
            v-if="store.selectedCategories.length > 0"
            class="inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--app-bg)] px-1 text-[10px] font-semibold text-[var(--app-ink)]"
          >
            {{ store.selectedCategories.length }}
          </span>
        </button>
      </template>
    </UiPageHeader>

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

    <DashboardCoverageMap class="min-h-0 flex-1" />
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, WritableComputedRef } from 'vue'
import { computed, onMounted } from 'vue'
import type { CoverageMember } from '~/services/dashboardService'
import type { SelectFieldOption } from '~/types/SelectField'
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

const store: ReturnType<typeof useCoverageStore> = useCoverageStore()
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

/** Organization members selectable as scopes. */
const members: ComputedRef<CoverageMember[]> = computed((): CoverageMember[] => store.coverage?.members ?? [])

/** Whose prospects the map shows: mine, the whole organization, or one member's. */
const scopeOptions: ComputedRef<SelectFieldOption[]> = computed((): SelectFieldOption[] => [
  { value: 'me', label: 'Mes prospects' },
  { value: 'org', label: "Toute l'organisation" },
  ...members.value.map(
    (member: CoverageMember): SelectFieldOption => ({
      value: `member:${member.user_id}`,
      label: member.name,
    }),
  ),
])

/** Selected scope — reloading the map is part of changing it. */
const scope: WritableComputedRef<string> = computed({
  get: (): string => store.scope,
  set: (value: string): void => {
    store.scope = value
    void store.load()
  },
})

/** Open the filters & zones drawer. */
function openFiltersDrawer(): void {
  drawerStack.push({ kind: 'coverage-filters' })
}

onMounted((): void => {
  void store.load()
})
</script>
