<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-4 @2xl:flex-row @2xl:items-end @2xl:justify-between">
      <div class="min-w-0">
        <p class="app-label flex items-center gap-2">
          <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
          Prospection
        </p>
        <h1 class="app-page-title mt-2">Trouver des prospects</h1>
        <p class="mt-1.5 text-sm text-[var(--app-ink-soft)]">
          Donnez un objectif : l'app cherche, vérifie chaque entreprise et garde celles qui le tiennent.
        </p>
      </div>
      <button
        type="button"
        class="app-btn-primary h-11 w-full px-4 text-sm whitespace-nowrap @2xl:h-9 @2xl:w-auto @2xl:text-xs"
        @click="openSearchDrawer"
      >
        <UIcon name="i-lucide-search" class="h-3.5 w-3.5" />
        Nouvelle recherche
      </button>
    </div>

    <div v-if="isLoadingSearches" class="flex items-center justify-center py-16">
      <UIcon name="i-lucide-loader-circle" class="h-8 w-8 animate-spin text-[var(--app-accent)]" />
    </div>

    <UiEmptyState
      v-else-if="store.currentSearch === null && store.recentSearches.length === 0"
      title="Aucune recherche pour l'instant"
      description="Indiquez des métiers, un pays et le nombre de prospects voulu. Chaque entreprise gardée arrive avec ses preuves, chaque entreprise écartée avec sa raison."
    >
      <template #action>
        <button type="button" class="app-btn-primary" @click="openSearchDrawer">
          <UIcon name="i-lucide-search" class="h-3.5 w-3.5" />
          Lancer une recherche
        </button>
      </template>
    </UiEmptyState>

    <template v-else>
      <template v-if="store.currentSearch">
        <ProspectSearchProgressCard
          :search="store.currentSearch"
          :is-cancelling="store.isCancelling"
          :is-resuming="store.isResuming"
          @cancel="cancelSearch"
          @resume="resumeSearch"
        />

        <ProspectSearchFacebookBanner
          v-if="store.waitingFacebookPageCount > 0 || facebookReading !== null"
          :waiting-page-count="store.waitingFacebookPageCount"
          :can-read-locally="store.canReadFacebookPagesLocally"
          :is-search-active="store.isCurrentSearchActive"
          :reading="facebookReading"
          @retry="store.retryFacebookReading()"
        />

        <ProspectSearchResultsCard
          :search="store.currentSearch"
          :busy-candidate-ids="store.busyCandidateIds"
          :opening-prospect-id="openingProspectId"
          @open-prospect="openProspect"
          @keep-candidate="keepCandidate"
          @reject-candidate="rejectCandidate"
        />
      </template>

      <ProspectSearchRecentList
        v-if="store.recentSearches.length > 0"
        :searches="store.recentSearches"
        :selected-search-id="store.currentSearch?.id ?? null"
        :loading-search-id="store.loadingSearchId"
        @select="selectSearch"
      />
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { Prospect } from '~/types'
import type { UseDashboardScrollReturn, UseToastReturn } from '~/types/Composables'
import type { ProspectSearchFacebookReading } from '~/types/ProspectSearch'
import { computed, onMounted, ref } from 'vue'
import { useDashboardScroll } from '~/composables/useDashboardScroll'
import { useToast } from '~/composables/useToast'
import { ProspectsService } from '~/services/prospectsService'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useProspectSearchStore } from '~/stores/prospectSearch'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

const store: ReturnType<typeof useProspectSearchStore> = useProspectSearchStore()
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()
const toast: UseToastReturn = useToast()
const { scrollToTop }: UseDashboardScrollReturn = useDashboardScroll()

const isLoadingSearches: Ref<boolean> = ref(store.currentSearch === null && store.recentSearches.length === 0)
const openingProspectId: Ref<number | null> = ref(null)

const facebookReading: ComputedRef<ProspectSearchFacebookReading | null> = computed(
  (): ProspectSearchFacebookReading | null => {
    const reading: ProspectSearchFacebookReading | null = store.facebookReading
    if (reading === null || reading.searchId !== store.currentSearch?.id) return null
    return reading.isRunning || reading.errorMessage !== null ? reading : null
  },
)

/** Open the objective form. */
function openSearchDrawer(): void {
  drawerStack.push({ kind: 'search-prospects' })
}

/**
 * Stop the followed search.
 * @returns A promise resolved once the search is stopped, or the failure is reported.
 */
async function cancelSearch(): Promise<void> {
  try {
    await store.cancelSearch()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Impossible d'arrêter la recherche")
  }
}

/**
 * Carry on the followed search.
 * @returns A promise resolved once the search runs again, or the failure is reported.
 */
async function resumeSearch(): Promise<void> {
  try {
    await store.resumeSearch()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Impossible de poursuivre la recherche')
  }
}

/**
 * Follow a search of the recent list and bring its progress into view.
 * @param searchId - Identifier of the clicked search.
 * @returns A promise resolved once the search is loaded, or the failure is reported.
 */
async function selectSearch(searchId: number): Promise<void> {
  if (searchId === store.currentSearch?.id) {
    scrollToTop()
    return
  }
  try {
    await store.loadSearch(searchId)
    scrollToTop()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Impossible de charger cette recherche')
  }
}

/**
 * Keep a candidate by hand: it becomes a prospect.
 * @param candidateId - The candidate to keep.
 * @returns A promise resolved once the candidate is kept, or the refusal is reported.
 */
async function keepCandidate(candidateId: number): Promise<void> {
  try {
    await store.keepCandidate(candidateId)
    toast.success('Candidat gardé : il est dans vos prospects')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Impossible de garder ce candidat')
  }
}

/**
 * Discard a candidate by hand: no later search proposes it again.
 * @param candidateId - The candidate to discard.
 * @returns A promise resolved once the candidate is discarded, or the refusal is reported.
 */
async function rejectCandidate(candidateId: number): Promise<void> {
  try {
    await store.rejectCandidate(candidateId)
    toast.success('Candidat écarté')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Impossible d'écarter ce candidat")
  }
}

/**
 * Open the record of the prospect a candidate became, stacked as a drawer.
 * @param prospectId - Identifier of the prospect.
 * @returns A promise resolved once the drawer is open, or the failure is reported.
 */
async function openProspect(prospectId: number): Promise<void> {
  if (openingProspectId.value !== null) return
  openingProspectId.value = prospectId
  try {
    const prospect: Prospect = await ProspectsService.getProspect(prospectId)
    drawerStack.push({ kind: 'prospect', prospect })
  } catch {
    toast.error("Cette fiche n'existe plus dans vos prospects")
  } finally {
    openingProspectId.value = null
  }
}

onMounted(async (): Promise<void> => {
  try {
    await store.restoreLatestSearch()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Impossible de charger vos recherches')
  } finally {
    isLoadingSearches.value = false
  }
})
</script>
