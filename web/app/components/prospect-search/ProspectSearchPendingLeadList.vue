<template>
  <div class="space-y-3">
    <div
      v-if="!store.hasLoadedPendingCandidates && store.isRefreshFailing"
      class="app-card border-[var(--app-red)]/40 bg-[var(--app-red-soft)] p-5"
    >
      <p class="font-semibold text-[var(--app-red)]">Erreur</p>
      <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
        Impossible de charger les leads à valider. Nouvelle tentative dans quelques secondes.
      </p>
    </div>

    <div v-else-if="!store.hasLoadedPendingCandidates" class="flex items-center justify-center py-16">
      <UIcon name="i-lucide-loader-circle" class="h-8 w-8 animate-spin text-[var(--app-accent)]" />
    </div>

    <div v-else-if="props.candidates.length === 0" class="app-card px-6 py-12 text-center">
      <LandingAsterisk class="text-4xl text-[var(--app-accent)]" />
      <h3 class="font-display mt-5 text-2xl font-semibold text-[var(--app-ink)]">{{ emptyLeadsNotice.title }}</h3>
      <p class="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-[var(--app-ink-soft)]">
        {{ emptyLeadsNotice.description }}
      </p>
      <NuxtLink
        v-if="emptyLeadsNotice.shouldOfferNewSearch"
        :to="PROSPECT_SEARCH_PAGE_PATH"
        class="app-btn-primary mt-6 inline-flex"
      >
        <UIcon name="i-lucide-search" class="h-3.5 w-3.5" />
        Nouvelle recherche
      </NuxtLink>
    </div>

    <template v-else>
      <button
        v-if="hiddenNewLeadCount > 0"
        type="button"
        class="flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl border border-[var(--app-accent)]/40 bg-[var(--app-accent-soft)] px-4 py-2.5 text-xs font-medium text-[var(--app-accent-ink)] transition-colors hover:border-[var(--app-accent)]"
        @click="showNewLeads"
      >
        <UIcon name="i-lucide-arrow-down-to-line" class="h-3.5 w-3.5" />
        {{ hiddenNewLeadCount > 1 ? `${hiddenNewLeadCount} nouveaux leads à afficher` : '1 nouveau lead à afficher' }}
      </button>

      <div v-if="displayedLeads.length > 0" class="app-card overflow-hidden">
        <ProspectSearchLeadTable
          :candidates="displayedLeads"
          :selected-candidate-ids="selectedLeadIds"
          @open="openLead"
          @accept="decisions.acceptLead"
          @reject="decisions.rejectLead"
          @toggle-select="toggleLeadSelection"
          @toggle-select-all="toggleAllLeadsSelection"
        />
        <div
          class="font-label border-t border-[var(--app-line)] bg-[var(--app-surface-2)]/50 px-4 py-3.5 text-xs text-[var(--app-ink-soft)] sm:px-6"
        >
          {{ displayedLeads.length > 1 ? `${displayedLeads.length} leads à valider` : '1 lead à valider' }}
        </div>
      </div>
    </template>

    <Transition name="bulkbar">
      <div
        v-if="selectedLeads.length > 0"
        class="fixed inset-x-0 bottom-0 z-40 flex justify-center px-0 sm:bottom-[calc(1.5rem+env(safe-area-inset-bottom))] sm:px-4"
      >
        <div
          class="app-card w-full rounded-t-2xl rounded-b-none border-x-0 border-b-0 px-4 pt-2 pb-[calc(1rem+env(safe-area-inset-bottom))] shadow-[var(--app-shadow-soft)] backdrop-blur sm:hidden"
        >
          <div class="mx-auto mb-3 h-1 w-9 rounded-full bg-[var(--app-line)]"></div>
          <div class="mb-3 flex items-center justify-between">
            <span class="font-label text-xs font-medium text-[var(--app-ink)]">{{ selectedLeadsLabel }}</span>
            <button
              type="button"
              class="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
              aria-label="Désélectionner tout"
              @click="clearLeadSelection"
            >
              <UIcon name="i-lucide-x" class="h-4 w-4" />
            </button>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <button
              type="button"
              class="app-btn-secondary h-11 w-full"
              :disabled="isSendingSelectedDecisions"
              @click="rejectSelectedLeads"
            >
              <UIcon name="i-lucide-x" class="h-4 w-4" />Refuser ({{ selectedLeads.length }})
            </button>
            <button
              type="button"
              class="app-btn-primary h-11 w-full"
              :disabled="isSendingSelectedDecisions"
              @click="acceptSelectedLeads"
            >
              <UIcon
                :name="isSendingSelectedDecisions ? 'i-lucide-loader-circle' : 'i-lucide-check'"
                :class="['h-4 w-4', isSendingSelectedDecisions && 'animate-spin']"
              />Accepter ({{ selectedLeads.length }})
            </button>
          </div>
        </div>

        <div
          class="app-card hidden flex-wrap items-center justify-center gap-2 rounded-full px-4 py-2.5 shadow-[var(--app-shadow-soft)] backdrop-blur sm:flex"
        >
          <span class="font-label px-1.5 text-xs font-medium text-[var(--app-ink)]">{{ selectedLeadsLabel }}</span>
          <span class="h-5 w-px bg-[var(--app-line)]"></span>
          <button
            type="button"
            class="app-btn-secondary h-9 px-4 text-xs"
            :disabled="isSendingSelectedDecisions"
            @click="rejectSelectedLeads"
          >
            <UIcon name="i-lucide-x" class="h-3.5 w-3.5" />Refuser ({{ selectedLeads.length }})
          </button>
          <button
            type="button"
            class="app-btn-primary h-9 px-4 text-xs"
            :disabled="isSendingSelectedDecisions"
            @click="acceptSelectedLeads"
          >
            <UIcon
              :name="isSendingSelectedDecisions ? 'i-lucide-loader-circle' : 'i-lucide-check'"
              :class="['h-3.5 w-3.5', isSendingSelectedDecisions && 'animate-spin']"
            />Accepter ({{ selectedLeads.length }})
          </button>
          <button
            type="button"
            class="ml-0.5 cursor-pointer rounded-full p-2 text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            aria-label="Désélectionner tout"
            @click="clearLeadSelection"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import type { UseProspectSearchDecisionsReturn } from '~/types/Composables'
import type { ProspectSearchCandidate, ProspectSearchEmptyLeadsNotice } from '~/types/ProspectSearch'
import type { ProspectSearchPendingLeadListProps } from '~/types/ProspectSearchPendingLeadList'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useProspectSearchDecisions } from '~/composables/useProspectSearchDecisions'
import { PROSPECT_SEARCH_EMPTY_LEADS_NOTICES, PROSPECT_SEARCH_PAGE_PATH } from '~/constants/prospectSearch'
import { useProspectSearchStore } from '~/stores/prospectSearch'

/** The « À valider » tab: leads arriving while it is on screen wait behind a line instead of moving the rows. */
const props: ProspectSearchPendingLeadListProps = defineProps({
  candidates: {
    type: Array as PropType<ProspectSearchCandidate[]>,
    required: true,
  },
})

const store: ReturnType<typeof useProspectSearchStore> = useProspectSearchStore()
const decisions: UseProspectSearchDecisionsReturn = useProspectSearchDecisions()

const selectedLeadIds: Ref<number[]> = ref([])
const displayedLeadIds: Ref<number[]> = ref([])
const isSendingSelectedDecisions: Ref<boolean> = ref(false)

const displayedLeads: ComputedRef<ProspectSearchCandidate[]> = computed((): ProspectSearchCandidate[] =>
  props.candidates.filter((lead: ProspectSearchCandidate): boolean => displayedLeadIds.value.includes(lead.id)),
)

const hiddenNewLeadCount: ComputedRef<number> = computed(
  (): number => props.candidates.length - displayedLeads.value.length,
)

const selectedLeads: ComputedRef<ProspectSearchCandidate[]> = computed((): ProspectSearchCandidate[] =>
  displayedLeads.value.filter((lead: ProspectSearchCandidate): boolean => selectedLeadIds.value.includes(lead.id)),
)

const selectedLeadsLabel: ComputedRef<string> = computed(
  (): string => `${selectedLeads.value.length} sélectionné${selectedLeads.value.length > 1 ? 's' : ''}`,
)

const emptyLeadsNotice: ComputedRef<ProspectSearchEmptyLeadsNotice> = computed((): ProspectSearchEmptyLeadsNotice => {
  if (store.pendingCandidates.length > 0) return PROSPECT_SEARCH_EMPTY_LEADS_NOTICES.noMatchingLead
  if (store.activeSearch !== null) return PROSPECT_SEARCH_EMPTY_LEADS_NOTICES.searchRunning
  return PROSPECT_SEARCH_EMPTY_LEADS_NOTICES.nothingToDecide
})

/** Show every waiting lead in the table, the ones that arrived since the tab was opened included. */
function showNewLeads(): void {
  displayedLeadIds.value = store.pendingCandidates.map((lead: ProspectSearchCandidate): number => lead.id)
}

/**
 * Open the record of a lead, walking the leads the table shows.
 * @param lead - The lead whose row was clicked.
 */
function openLead(lead: ProspectSearchCandidate): void {
  decisions.openLead(lead, displayedLeads.value)
}

/**
 * Tick or untick one lead.
 * @param lead - The lead whose checkbox was toggled.
 */
function toggleLeadSelection(lead: ProspectSearchCandidate): void {
  selectedLeadIds.value = selectedLeadIds.value.includes(lead.id)
    ? selectedLeadIds.value.filter((id: number): boolean => id !== lead.id)
    : [...selectedLeadIds.value, lead.id]
}

/**
 * Tick or untick every lead the table shows.
 * @param checked - True to select them all.
 */
function toggleAllLeadsSelection(checked: boolean): void {
  selectedLeadIds.value = checked ? displayedLeads.value.map((lead: ProspectSearchCandidate): number => lead.id) : []
}

/** Untick every lead. */
function clearLeadSelection(): void {
  selectedLeadIds.value = []
}

/**
 * Accept every ticked lead: they become prospects.
 * @returns A promise resolved once the decisions are sent and told.
 */
async function acceptSelectedLeads(): Promise<void> {
  if (isSendingSelectedDecisions.value) return
  isSendingSelectedDecisions.value = true
  try {
    await decisions.acceptLeads(selectedLeads.value)
  } finally {
    isSendingSelectedDecisions.value = false
  }
}

/**
 * Refuse every ticked lead.
 * @returns A promise resolved once the decisions are sent and told.
 */
async function rejectSelectedLeads(): Promise<void> {
  if (isSendingSelectedDecisions.value) return
  isSendingSelectedDecisions.value = true
  try {
    await decisions.rejectLeads(selectedLeads.value)
  } finally {
    isSendingSelectedDecisions.value = false
  }
}

watch(
  (): ProspectSearchCandidate[] => store.pendingCandidates,
  (waitingLeads: ProspectSearchCandidate[]): void => {
    const waitingIds: number[] = waitingLeads.map((lead: ProspectSearchCandidate): number => lead.id)
    selectedLeadIds.value = selectedLeadIds.value.filter((id: number): boolean => waitingIds.includes(id))
    const hasDisplayedLead: boolean = displayedLeadIds.value.some((id: number): boolean => waitingIds.includes(id))
    if (!hasDisplayedLead) showNewLeads()
  },
)

onMounted((): void => {
  showNewLeads()
  store.setPendingTabDisplayed(true)
})

onBeforeUnmount((): void => {
  store.setPendingTabDisplayed(false)
})
</script>

<style scoped>
.bulkbar-enter-active,
.bulkbar-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.bulkbar-enter-from,
.bulkbar-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

@media (prefers-reduced-motion: reduce) {
  .bulkbar-enter-active,
  .bulkbar-leave-active {
    transition: none;
  }
  .bulkbar-enter-from,
  .bulkbar-leave-to {
    transform: none;
  }
}
</style>
