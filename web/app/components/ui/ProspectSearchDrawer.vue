<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="props.open"
        class="fixed top-0 right-0 bottom-[var(--app-drawer-bottom)] z-50 flex w-full max-w-[460px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[var(--app-drawer-bottom-padding)] shadow-2xl"
      >
        <UiDrawerHeader
          :title="drawerTitle"
          icon="i-lucide-search"
          :show-back="props.showBack"
          @back="emit('back')"
          @close="emit('close')"
        >
          <template v-if="search" #badges>
            <div class="mb-1 flex flex-wrap items-center gap-1.5">
              <span :class="['app-badge', searchStatus.badgeClass]">
                <UIcon v-if="isSearchActive" name="i-lucide-loader-circle" class="h-3 w-3 animate-spin" />
                {{ searchStatus.label }}
              </span>
            </div>
          </template>
          <template #subtitle>
            <p v-if="search" class="mt-0.5 truncate text-sm text-[var(--app-ink-soft)]">
              {{ ProspectSearches.tradesLabel(search) }}
            </p>
          </template>
        </UiDrawerHeader>

        <div v-if="!search && store.isLoadingFollowedSearch" class="flex flex-1 items-center justify-center">
          <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin text-[var(--app-ink-soft)]" />
        </div>

        <div v-else-if="!search" class="flex flex-1 flex-col items-center justify-center gap-3 px-8 text-center">
          <UIcon name="i-lucide-search" class="h-7 w-7 text-[var(--app-faint)]" />
          <p class="text-sm leading-relaxed text-[var(--app-ink-soft)]">
            Aucune recherche pour l'instant. Donnez un objectif : l'app cherche, vérifie chaque entreprise et vous
            propose les leads.
          </p>
          <NuxtLink :to="PROSPECT_SEARCH_PAGE_PATH" class="app-btn-primary">
            <UIcon name="i-lucide-search" class="h-3.5 w-3.5" />
            Nouvelle recherche
          </NuxtLink>
        </div>

        <template v-else>
          <div class="flex-1 overflow-x-hidden overflow-y-auto">
            <div class="space-y-4 px-5 py-4">
              <div>
                <p class="text-xs leading-relaxed break-words text-[var(--app-ink)]">
                  {{ ProspectSearches.objectiveLabel(search) }}
                </p>
                <p class="font-label mt-1 text-[11px] text-[var(--app-ink-soft)]">
                  Lancée le {{ formatShortMonthDayTime(search.created_at) }} ·
                  {{ ProspectSearches.costLabel(search.request_count) }}
                </p>
              </div>

              <UiCallout v-if="search.status === 'failed' && search.error_message" variant="danger">
                {{ search.error_message }}
              </UiCallout>

              <ProspectSearchTradeProgressList
                v-if="search.trade_counts.length > 0"
                :trade-counts="search.trade_counts"
                should-show-details
              />

              <p
                v-if="isSearchActive && store.latestJournalMessage"
                class="flex items-start gap-2 text-xs leading-relaxed text-[var(--app-ink-soft)]"
                aria-live="polite"
              >
                <UIcon name="i-lucide-activity" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span class="line-clamp-2 min-w-0 break-words">{{ store.latestJournalMessage }}</span>
              </p>

              <ProspectSearchFacebookBanner
                v-if="store.waitingFacebookPageCount > 0 || facebookReading !== null"
                :waiting-page-count="store.waitingFacebookPageCount"
                :can-read-locally="store.canReadFacebookPagesLocally"
                :is-desktop-app-online="store.isDesktopAppOnline"
                :is-search-active="isSearchActive"
                :reading="facebookReading"
                @retry="store.retryFacebookReading"
              />
            </div>

            <section
              v-if="store.queuedSearches.length > 0"
              class="border-t border-[var(--app-line)] pb-1"
              aria-labelledby="prospect-search-drawer-queue-title"
            >
              <h3
                id="prospect-search-drawer-queue-title"
                class="flex items-center gap-2 px-5 pt-4 text-sm font-semibold text-[var(--app-ink)]"
              >
                File d'attente
                <span
                  class="font-label rounded-full bg-[var(--app-surface-2)] px-2 py-0.5 text-xs font-medium text-[var(--app-ink-soft)]"
                >
                  {{ store.queuedSearches.length }}
                </span>
              </h3>
              <p class="px-5 pt-1 pb-2 text-[11px] leading-relaxed text-[var(--app-ink-soft)]">
                Elles démarrent toutes seules, l'une après l'autre, à la fin de la recherche en cours.
              </p>
              <ol class="divide-y divide-[var(--app-line-soft)]">
                <li
                  v-for="(queued, position) in store.queuedSearches"
                  :key="queued.id"
                  class="flex items-center gap-3 px-5 py-2.5"
                >
                  <span
                    class="font-label flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[var(--app-line)] text-[11px] text-[var(--app-ink-soft)] tabular-nums"
                    aria-hidden="true"
                  >
                    {{ position + 1 }}
                  </span>
                  <div class="min-w-0 flex-1">
                    <p class="truncate text-sm font-medium text-[var(--app-ink)]">
                      {{ ProspectSearches.tradesLabel(queued) }}
                    </p>
                    <p
                      class="truncate text-[11px] text-[var(--app-ink-soft)]"
                      :title="ProspectSearches.objectiveLabel(queued)"
                    >
                      {{ queued.count_per_trade }} par métier · {{ ProspectSearches.placeLabel(queued) }}
                    </p>
                  </div>
                  <button
                    type="button"
                    class="app-btn-secondary h-8 min-h-8 shrink-0 px-3 text-xs pointer-coarse:min-h-11 pointer-coarse:text-sm"
                    :disabled="store.cancellingQueuedSearchIds.includes(queued.id)"
                    :aria-label="`Retirer ${ProspectSearches.tradesLabel(queued)} de la file`"
                    @click="removeFromQueue(queued)"
                  >
                    Retirer
                  </button>
                </li>
              </ol>
            </section>

            <section class="border-t border-[var(--app-line)]" aria-labelledby="prospect-search-drawer-leads-title">
              <h3
                id="prospect-search-drawer-leads-title"
                class="flex items-center gap-2 px-5 pt-4 pb-2 text-sm font-semibold text-[var(--app-ink)]"
              >
                Leads à valider
                <span
                  class="font-label rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="
                    leads.length > 0
                      ? 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
                      : 'bg-[var(--app-surface-2)] text-[var(--app-ink-soft)]'
                  "
                >
                  {{ leads.length }}
                </span>
              </h3>
              <ul v-if="leads.length > 0" class="divide-y divide-[var(--app-line-soft)]">
                <li
                  v-for="lead in leads"
                  :key="lead.id"
                  class="px-5 py-2.5 transition-colors hover:bg-[var(--app-surface-2)]/50"
                >
                  <div class="flex items-center gap-3">
                    <button
                      type="button"
                      class="min-w-0 flex-1 cursor-pointer truncate text-left text-sm font-medium text-[var(--app-ink)] underline decoration-transparent underline-offset-4 transition-colors hover:decoration-[var(--app-accent)]"
                      :title="`Ouvrir la fiche de ${lead.name}`"
                      @click="decisions.openLead(lead, leads)"
                    >
                      {{ lead.name }}
                    </button>
                    <ProspectSearchLeadCriteria :candidate="lead" />
                  </div>
                  <div class="mt-1.5 flex items-center gap-2">
                    <span class="min-w-0 flex-1 truncate text-[11px] text-[var(--app-ink-soft)]">
                      {{ store.buildTradeAndTownLabel(lead) }}
                    </span>
                    <button
                      type="button"
                      class="app-btn-secondary h-8 min-h-8 shrink-0 px-3 text-xs pointer-coarse:min-h-11 pointer-coarse:text-sm"
                      :disabled="store.busyCandidateIds.includes(lead.id)"
                      @click="decisions.rejectLead(lead)"
                    >
                      Refuser
                    </button>
                    <button
                      type="button"
                      class="app-btn-primary h-8 min-h-8 shrink-0 px-3 text-xs pointer-coarse:min-h-11 pointer-coarse:text-sm"
                      :disabled="store.busyCandidateIds.includes(lead.id)"
                      @click="decisions.acceptLead(lead)"
                    >
                      <UIcon
                        :name="store.busyCandidateIds.includes(lead.id) ? 'i-lucide-loader-circle' : 'i-lucide-check'"
                        :class="['h-3.5 w-3.5', store.busyCandidateIds.includes(lead.id) && 'animate-spin']"
                      />
                      Accepter
                    </button>
                  </div>
                </li>
              </ul>
              <p v-else class="px-5 pb-4 text-xs leading-relaxed text-[var(--app-ink-soft)]">
                {{
                  isSearchActive
                    ? 'Les leads arrivent ici dès que la recherche les a vérifiés.'
                    : 'Aucun lead de cette recherche n’attend votre décision.'
                }}
              </p>
            </section>

            <div class="space-y-3 border-t border-[var(--app-line)] px-5 py-4">
              <UiCollapsibleCard
                v-if="rejectedReasonCounts.length > 0"
                icon="i-lucide-filter-x"
                title="Entreprises écartées"
                :suffix="String(rejectedCandidates.length)"
              >
                <ul class="divide-y divide-[var(--app-line-soft)]">
                  <li
                    v-for="reason in rejectedReasonCounts"
                    :key="reason.key"
                    class="flex items-baseline justify-between gap-3 px-4 py-2 text-xs"
                  >
                    <span class="min-w-0 text-[var(--app-ink)]">{{ reason.label }}</span>
                    <span class="font-label shrink-0 text-[var(--app-ink-soft)] tabular-nums">{{ reason.count }}</span>
                  </li>
                </ul>
              </UiCollapsibleCard>

              <UiCollapsibleCard
                icon="i-lucide-scroll-text"
                title="Journal complet"
                :suffix="`${search.journal.length} ${search.journal.length > 1 ? 'lignes' : 'ligne'}`"
              >
                <ProspectSearchJournal :lines="search.journal" />
              </UiCollapsibleCard>
            </div>
          </div>

          <div class="flex flex-col gap-2 border-t border-[var(--app-line)] px-5 py-4 sm:flex-row">
            <button type="button" class="app-btn-secondary w-full sm:flex-1" @click="showAllLeads">
              <UIcon name="i-lucide-list-checks" class="h-3.5 w-3.5" />
              Voir tous les leads
            </button>
            <button
              v-if="isSearchActive"
              type="button"
              class="app-btn-secondary w-full sm:flex-1"
              :disabled="store.isCancelling"
              @click="cancelSearch"
            >
              <UIcon
                :name="store.isCancelling ? 'i-lucide-loader-circle' : 'i-lucide-circle-stop'"
                :class="['h-3.5 w-3.5', store.isCancelling && 'animate-spin']"
              />
              Arrêter la recherche
            </button>
            <button
              v-else-if="search.status === 'queued'"
              type="button"
              class="app-btn-secondary w-full sm:flex-1"
              :disabled="store.cancellingQueuedSearchIds.includes(search.id)"
              @click="removeFromQueue(search)"
            >
              <UIcon name="i-lucide-list-x" class="h-3.5 w-3.5" />
              Retirer de la file
            </button>
            <button
              v-else-if="canResumeSearch"
              type="button"
              class="app-btn-primary w-full sm:flex-1"
              :disabled="store.isResuming"
              @click="resumeSearch"
            >
              <UIcon
                :name="store.isResuming ? 'i-lucide-loader-circle' : 'i-lucide-play'"
                :class="['h-3.5 w-3.5', store.isResuming && 'animate-spin']"
              />
              Poursuivre
            </button>
          </div>
        </template>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn } from 'vue'
import type { UseProspectSearchDecisionsReturn, UseToastReturn } from '~/types/Composables'
import type {
  ProspectSearchCandidate,
  ProspectSearchDetail,
  ProspectSearchFacebookReading,
  ProspectSearchRejectReason,
  ProspectSearchSummary,
} from '~/types/ProspectSearch'
import type { StatusPresentation } from '~/types/StatusPresentation'
import type {
  ProspectSearchRejectedReasonCount,
  UiProspectSearchDrawerEmits,
  UiProspectSearchDrawerProps,
} from '~/types/UiProspectSearchDrawer'
import { computed, watch } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { useProspectSearchDecisions } from '~/composables/useProspectSearchDecisions'
import { useToast } from '~/composables/useToast'
import {
  MY_PROSPECTS_PAGE_PATH,
  PROSPECT_SEARCH_PAGE_PATH,
  PROSPECT_SEARCH_REJECT_REASON_LABELS,
  PROSPECT_SEARCH_REJECT_REASON_ORDER,
  PROSPECT_SEARCH_STATUS_PRESENTATION,
  PROSPECT_SEARCH_UNEXPLAINED_REJECT_LABEL,
} from '~/constants/prospectSearch'
import { useProspectSearchStore } from '~/stores/prospectSearch'
import { formatShortMonthDayTime } from '~/utils/date'
import { ProspectSearches } from '~/utils/prospectSearches'

/** The followed search, from any page: its progress, its Facebook page reading and the leads it waits a decision on. */
const props: UiProspectSearchDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiProspectSearchDrawerEmits> = defineEmits<UiProspectSearchDrawerEmits>()

const store: ReturnType<typeof useProspectSearchStore> = useProspectSearchStore()
const decisions: UseProspectSearchDecisionsReturn = useProspectSearchDecisions()
const route: ReturnType<typeof useRoute> = useRoute()
const toast: UseToastReturn = useToast()

const isDrawerCoveringPage: ComputedRef<boolean> = useMediaQuery('(max-width: 767px)')

const search: ComputedRef<ProspectSearchDetail | null> = computed(
  (): ProspectSearchDetail | null => store.followedSearch,
)

const isSearchActive: ComputedRef<boolean> = computed((): boolean => store.isFollowedSearchActive)

const drawerTitle: ComputedRef<string> = computed((): string => {
  if (isSearchActive.value) return 'Recherche en cours'
  return search.value?.status === 'queued' ? "Recherche en file d'attente" : 'Dernière recherche'
})

const canResumeSearch: ComputedRef<boolean> = computed(
  (): boolean => search.value !== null && ProspectSearches.canResume(search.value),
)

const searchStatus: ComputedRef<StatusPresentation> = computed(
  (): StatusPresentation => PROSPECT_SEARCH_STATUS_PRESENTATION[search.value?.status ?? 'pending'],
)

const leads: ComputedRef<ProspectSearchCandidate[]> = computed(
  (): ProspectSearchCandidate[] => store.followedSearchPendingCandidates,
)

const facebookReading: ComputedRef<ProspectSearchFacebookReading | null> = computed(
  (): ProspectSearchFacebookReading | null => {
    const reading: ProspectSearchFacebookReading | null = store.facebookReading
    if (reading === null || reading.searchId !== search.value?.id) return null
    return reading.isRunning || reading.errorMessage !== null ? reading : null
  },
)

const rejectedCandidates: ComputedRef<ProspectSearchCandidate[]> = computed((): ProspectSearchCandidate[] =>
  (search.value?.candidates ?? []).filter(
    (candidate: ProspectSearchCandidate): boolean => candidate.status === 'rejected',
  ),
)

const rejectedReasonCounts: ComputedRef<ProspectSearchRejectedReasonCount[]> = computed(
  (): ProspectSearchRejectedReasonCount[] => {
    const reasonCounts: ProspectSearchRejectedReasonCount[] = PROSPECT_SEARCH_REJECT_REASON_ORDER.map(
      (reason: ProspectSearchRejectReason): ProspectSearchRejectedReasonCount => ({
        key: reason,
        label: PROSPECT_SEARCH_REJECT_REASON_LABELS[reason],
        count: rejectedCandidates.value.filter(
          (candidate: ProspectSearchCandidate): boolean => candidate.reject_reason === reason,
        ).length,
      }),
    )
    const unexplainedCount: number = rejectedCandidates.value.filter(
      (candidate: ProspectSearchCandidate): boolean =>
        candidate.reject_reason === null || !PROSPECT_SEARCH_REJECT_REASON_ORDER.includes(candidate.reject_reason),
    ).length
    reasonCounts.push({ key: 'unexplained', label: PROSPECT_SEARCH_UNEXPLAINED_REJECT_LABEL, count: unexplainedCount })
    return reasonCounts.filter((reason: ProspectSearchRejectedReasonCount): boolean => reason.count > 0)
  },
)

/**
 * Stop the running search.
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
 * Take a search out of the queue before it starts.
 * @param queued - The queued search.
 * @returns A promise resolved once the search left the queue, or the failure is reported.
 */
async function removeFromQueue(queued: ProspectSearchSummary): Promise<void> {
  try {
    await store.cancelQueuedSearch(queued.id)
    toast.info(`« ${ProspectSearches.tradesLabel(queued)} » retirée de la file`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Impossible de retirer cette recherche de la file')
  }
}

/**
 * Carry on the search that stopped short of its objective.
 * @returns A promise resolved once the search runs again, or the failure is reported.
 */
async function resumeSearch(): Promise<void> {
  try {
    await store.resumeSearch()
    if (store.followedSearch?.status === 'queued') {
      toast.info('Recherche ajoutée à la file : elle reprendra toute seule après celle en cours')
    }
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Impossible de poursuivre la recherche')
  }
}

/** Show the « À valider » tab of the prospects page; on a phone the drawer closes to let it be seen. */
function showAllLeads(): void {
  const isAlreadyOnProspectsPage: boolean = route.path === MY_PROSPECTS_PAGE_PATH
  decisions.showPendingLeads()
  if (isAlreadyOnProspectsPage && isDrawerCoveringPage.value) emit('close')
}

watch(
  (): boolean => props.open,
  (isOpen: boolean): void => {
    if (!isOpen || import.meta.server) return
    store.loadLatestSearch().catch((): void => {
      toast.error('Impossible de charger votre dernière recherche')
    })
  },
  { immediate: true },
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
