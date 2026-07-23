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
            <UIcon name="i-lucide-map-pin" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </span>
          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">{{ zone?.label ?? '' }}</h2>
            <p class="mt-0.5 text-[11px] text-[var(--app-ink-soft)]">
              <span v-if="isLoading">Chargement…</span>
              <span v-else>{{ total }} prospect{{ total > 1 ? 's' : '' }} dans cette zone</span>
            </p>
          </div>
          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <!-- Body -->
        <div class="flex-1 overflow-y-auto px-5 py-3">
          <div v-if="isLoading" class="flex h-40 items-center justify-center">
            <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin text-[var(--app-ink-soft)]" />
          </div>

          <p v-else-if="rows.length === 0" class="text-muted py-8 text-center text-sm">
            Aucun prospect dans cette zone pour ces filtres.
          </p>

          <p
            v-if="!isLoading && rows.length > 0"
            class="text-muted flex items-center justify-end gap-3 px-3 pb-1.5 text-[10px]"
          >
            <span class="inline-flex items-center gap-1"><UIcon name="i-lucide-send" class="h-3 w-3" /> envoyés</span>
            <span class="inline-flex items-center gap-1">
              <UIcon name="i-lucide-mail-open" class="h-3 w-3" /> ouverts
            </span>
            <span class="inline-flex items-center gap-1">
              <UIcon name="i-lucide-mouse-pointer-click" class="h-3 w-3" /> clics démo
            </span>
          </p>

          <ul v-if="!isLoading && rows.length > 0" class="space-y-0.5">
            <li v-for="row in rows" :key="row.id">
              <button
                type="button"
                class="flex w-full cursor-pointer items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-[var(--app-surface-2)]"
                :title="`Ouvrir ${row.name}`"
                @click="openProspect(row.id)"
              >
                <div class="min-w-0">
                  <p class="truncate text-sm font-medium text-[var(--app-ink)]">{{ row.name }}</p>
                  <p class="text-muted truncate text-[11px]">
                    {{ zone?.kind === 'region' ? (row.city ?? '—') : (row.category ?? '—') }}
                  </p>
                </div>
                <!-- Status recap: demo chip, visible email counts, sold chip -->
                <div class="flex shrink-0 items-center gap-2.5">
                  <span
                    v-if="row.has_demo"
                    class="inline-flex items-center gap-1 rounded-full bg-[var(--app-green)]/15 px-1.5 py-0.5 text-[10px] font-semibold text-[var(--app-green)]"
                    title="Site démo généré"
                  >
                    <UIcon name="i-lucide-app-window" class="h-3 w-3" />
                    Démo
                  </span>
                  <span
                    class="inline-flex items-center gap-1 text-[11px] tabular-nums"
                    :class="row.emails_sent > 0 ? 'text-[var(--app-ink)]' : 'text-[var(--app-faint)]'"
                    :title="`${row.emails_sent} email(s) envoyé(s)`"
                  >
                    <UIcon name="i-lucide-send" class="h-3.5 w-3.5" />
                    {{ row.emails_sent }}
                  </span>
                  <span
                    class="inline-flex items-center gap-1 text-[11px] tabular-nums"
                    :class="row.emails_opened > 0 ? 'text-[var(--app-ink)]' : 'text-[var(--app-faint)]'"
                    :title="`${row.emails_opened} ouverture(s)`"
                  >
                    <UIcon name="i-lucide-mail-open" class="h-3.5 w-3.5" />
                    {{ row.emails_opened }}
                  </span>
                  <span
                    class="inline-flex items-center gap-1 text-[11px] tabular-nums"
                    :class="row.emails_clicked > 0 ? 'text-[var(--app-ink)]' : 'text-[var(--app-faint)]'"
                    :title="`${row.emails_clicked} clic(s) sur le lien de démo`"
                  >
                    <UIcon name="i-lucide-mouse-pointer-click" class="h-3.5 w-3.5" />
                    {{ row.emails_clicked }}
                  </span>
                  <span
                    v-if="row.is_sold"
                    class="inline-flex items-center gap-1 rounded-full bg-[var(--app-green)]/15 px-1.5 py-0.5 text-[10px] font-semibold text-[var(--app-green)]"
                    title="Vendu"
                  >
                    <UIcon name="i-lucide-banknote" class="h-3 w-3" />
                    Vendu
                  </span>
                </div>
              </button>
            </li>
          </ul>

          <p v-if="!isLoading && total > rows.length" class="text-muted py-2 text-center text-[11px]">
            {{ rows.length }} affichés sur {{ total }}.
          </p>
        </div>

        <!-- Footer: relaunch a search in this zone -->
        <div class="border-t border-[var(--app-line)] px-5 py-3">
          <button type="button" class="btn-primary w-full text-sm" @click="prospectAgain">
            <UIcon name="i-lucide-search" class="mr-1.5 h-4 w-4" />
            Prospecter à nouveau ici
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import type { PropType, Ref } from 'vue'
import { ref, watch } from 'vue'
import type { CoverageProspectRow } from '~/services/dashboardService'
import { getCoverageProspects } from '~/services/dashboardService'
import { getProspect } from '~/services/prospectsService'
import { useCoverageStore } from '~/stores/coverage'
import { useDrawerStackStore } from '~/stores/drawerStack'
import type { CoverageZone } from '~/types/DrawerStack'

/**
 * Coverage zone drawer: airy prospect recap for a clicked map zone (city dot
 * or covered region) — demo / email engagement / sold at a glance, row click
 * opens the full prospect drawer, footer relaunches a search in the zone.
 */
const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
  zone: {
    type: Object as PropType<CoverageZone | null>,
    default: null,
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

const isLoading: Ref<boolean> = ref(false)
const rows: Ref<CoverageProspectRow[]> = ref([])
const total: Ref<number> = ref(0)

/**
 * Load the zone's prospects (same scope + trade filter as the map).
 * @returns A promise resolved once loaded.
 */
async function loadZone(): Promise<void> {
  const zone: CoverageZone | null = props.zone
  if (!zone || zone.cities.length === 0) {
    rows.value = []
    total.value = 0
    return
  }
  isLoading.value = true
  try {
    const [scopeName, memberId] = store.scope.startsWith('member:')
      ? (['member', Number(store.scope.slice('member:'.length))] as [string, number])
      : ([store.scope, undefined] as [string, undefined])
    const data = await getCoverageProspects(zone.cities, scopeName, memberId, store.selectedCategories)
    rows.value = data.items
    total.value = data.total
  } catch {
    rows.value = []
    total.value = 0
  } finally {
    isLoading.value = false
  }
}

/**
 * Open the full prospect drawer for a row (stacked — back returns to the list).
 * @param prospectId - Prospect to open.
 */
async function openProspect(prospectId: number): Promise<void> {
  try {
    const prospect = await getProspect(prospectId)
    drawerStack.push({ kind: 'prospect', prospect })
  } catch {
    // Row stays inert on fetch failure — the list itself already rendered.
  }
}

/** Open the search drawer prefilled with the zone's city (stacked). */
function prospectAgain(): void {
  drawerStack.push({
    kind: 'search-prospects',
    prefill: {
      ...(props.zone?.prefillCity ? { city: props.zone.prefillCity } : {}),
      ...(store.selectedCategories.length === 1 ? { category: store.selectedCategories[0] as string } : {}),
    },
  })
}

// Reload whenever the drawer opens on a (new) zone.
watch(
  (): [boolean, CoverageZone | null] => [props.open, props.zone],
  ([open]: [boolean, CoverageZone | null]): void => {
    if (open) void loadZone()
  },
  { immediate: true, deep: true },
)
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
