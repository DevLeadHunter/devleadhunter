<template>
  <section class="app-card min-w-0 overflow-hidden" aria-label="Candidats de la recherche">
    <div
      v-if="shouldRemindDecisions"
      class="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 border-b border-[var(--app-line)] bg-[var(--app-surface-2)]/60 px-4 py-2.5 @2xl:px-5"
    >
      <p class="flex min-w-0 items-center gap-2 text-xs font-medium text-[var(--app-ink)]">
        <UIcon name="i-lucide-circle-help" class="h-4 w-4 shrink-0 text-[var(--app-accent-ink)]" />
        {{ decisionReminderLabel }}
      </p>
      <button type="button" class="app-btn-secondary h-9 min-h-9 px-3 text-xs" @click="activeTab = 'to_confirm'">
        Décider
        <UIcon name="i-lucide-arrow-right" class="h-3.5 w-3.5" />
      </button>
    </div>
    <div class="border-b border-[var(--app-line)] px-1.5 pt-1">
      <UiFilterTabs :model-value="activeTab" :tabs="tabs" @update:model-value="selectTab" />
    </div>

    <ProspectSearchJournal v-if="activeTab === 'journal'" :lines="props.search.journal" />

    <template v-else-if="activeTab === 'rejected' && rejectedGroups.length > 0">
      <div
        v-for="group in rejectedGroups"
        :key="group.key"
        class="border-b border-[var(--app-line-soft)] last:border-b-0"
      >
        <button
          type="button"
          class="flex w-full cursor-pointer items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-[var(--app-surface-2)]/50 @2xl:px-5"
          :aria-expanded="expandedRejectedGroupKeys.includes(group.key)"
          @click="toggleRejectedGroup(group.key)"
        >
          <span class="flex min-w-0 flex-wrap items-center gap-2 text-sm font-medium text-[var(--app-ink)]">
            {{ group.label }}
            <span
              class="font-label rounded-full bg-[var(--app-surface-2)] px-2 py-0.5 text-xs text-[var(--app-ink-soft)]"
            >
              {{ group.candidates.length }}
            </span>
          </span>
          <UIcon
            name="i-lucide-chevron-down"
            :class="[
              'h-4 w-4 shrink-0 text-[var(--app-ink-soft)] transition-transform',
              expandedRejectedGroupKeys.includes(group.key) && 'rotate-180',
            ]"
          />
        </button>
        <ul
          v-if="expandedRejectedGroupKeys.includes(group.key)"
          class="divide-y divide-[var(--app-line-soft)] border-t border-[var(--app-line-soft)]"
        >
          <li v-for="candidate in group.candidates" :key="candidate.id">
            <ProspectSearchCandidateRow
              :candidate="candidate"
              :trade-label="tradeLabelOf(candidate)"
              :is-busy="props.busyCandidateIds.includes(candidate.id)"
              :is-opening-prospect="isOpeningProspectOf(candidate)"
              @open-prospect="emit('open-prospect', $event)"
              @keep="emit('keep-candidate', $event)"
              @reject="emit('reject-candidate', $event)"
            />
          </li>
        </ul>
      </div>
    </template>

    <ul v-else-if="activeCandidates.length > 0" class="divide-y divide-[var(--app-line-soft)]">
      <li v-for="candidate in activeCandidates" :key="candidate.id">
        <ProspectSearchCandidateRow
          :candidate="candidate"
          :trade-label="tradeLabelOf(candidate)"
          :is-busy="props.busyCandidateIds.includes(candidate.id)"
          :is-opening-prospect="isOpeningProspectOf(candidate)"
          @open-prospect="emit('open-prospect', $event)"
          @keep="emit('keep-candidate', $event)"
          @reject="emit('reject-candidate', $event)"
        />
      </li>
    </ul>

    <p v-else class="px-5 py-10 text-center text-sm text-[var(--app-ink-soft)]">{{ emptyTabLabel }}</p>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type {
  ProspectSearchCandidate,
  ProspectSearchCandidateStatus,
  ProspectSearchDetail,
  ProspectSearchRejectReason,
  ProspectSearchResultTabKey,
  ProspectSearchTradeCounts,
} from '~/types/ProspectSearch'
import type {
  ProspectSearchRejectedGroup,
  ProspectSearchResultsCardEmits,
  ProspectSearchResultsCardProps,
} from '~/types/ProspectSearchResultsCard'
import type { UiFilterTab } from '~/types/UiFilterTabs'
import { computed, ref, watch } from 'vue'
import {
  PROSPECT_SEARCH_EMPTY_TAB_LABELS,
  PROSPECT_SEARCH_REJECT_REASON_LABELS,
  PROSPECT_SEARCH_REJECT_REASON_ORDER,
  PROSPECT_SEARCH_RESULT_TAB_LABELS,
  PROSPECT_SEARCH_RESULT_TAB_ORDER,
} from '~/constants/prospectSearch'

/** Candidates of a search sliced by where they stand, the discarded ones grouped by reason, plus the journal. */
const props: ProspectSearchResultsCardProps = defineProps({
  search: {
    type: Object as PropType<ProspectSearchDetail>,
    required: true,
  },
  busyCandidateIds: {
    type: Array as PropType<number[]>,
    required: true,
  },
  openingProspectId: {
    type: Number as PropType<number | null>,
    default: null,
  },
})

const emit: EmitFn<ProspectSearchResultsCardEmits> = defineEmits<ProspectSearchResultsCardEmits>()

const DEFAULT_TAB: ProspectSearchResultTabKey = 'kept'
const UNEXPLAINED_REJECT_GROUP_KEY: string = 'unexplained'
const ALWAYS_SHOWN_TABS: string[] = ['kept', 'journal']

const activeTab: Ref<ProspectSearchResultTabKey> = ref(DEFAULT_TAB)
const expandedRejectedGroupKeys: Ref<string[]> = ref([])

const candidatesByStatus: ComputedRef<Record<ProspectSearchCandidateStatus, ProspectSearchCandidate[]>> = computed(
  (): Record<ProspectSearchCandidateStatus, ProspectSearchCandidate[]> => {
    const sliced: Record<ProspectSearchCandidateStatus, ProspectSearchCandidate[]> = {
      kept: [],
      set_aside: [],
      to_confirm: [],
      needs_browser: [],
      discovered: [],
      rejected: [],
    }
    for (const candidate of props.search.candidates) sliced[candidate.status].push(candidate)
    return sliced
  },
)

const tabs: ComputedRef<UiFilterTab[]> = computed((): UiFilterTab[] =>
  PROSPECT_SEARCH_RESULT_TAB_ORDER.map(
    (key: ProspectSearchResultTabKey): UiFilterTab => ({
      key,
      label: PROSPECT_SEARCH_RESULT_TAB_LABELS[key],
      count: key === 'journal' ? props.search.journal.length : candidatesByStatus.value[key].length,
    }),
  ).filter((tab: UiFilterTab): boolean => ALWAYS_SHOWN_TABS.includes(tab.key) || (tab.count ?? 0) > 0),
)

const shouldRemindDecisions: ComputedRef<boolean> = computed(
  (): boolean => candidatesByStatus.value.to_confirm.length > 0 && activeTab.value !== 'to_confirm',
)

const decisionReminderLabel: ComputedRef<string> = computed((): string => {
  const waitingCount: number = candidatesByStatus.value.to_confirm.length
  return waitingCount > 1 ? `${waitingCount} candidats attendent votre décision.` : '1 candidat attend votre décision.'
})

const activeCandidates: ComputedRef<ProspectSearchCandidate[]> = computed((): ProspectSearchCandidate[] =>
  activeTab.value === 'journal' ? [] : candidatesByStatus.value[activeTab.value],
)

const emptyTabLabel: ComputedRef<string> = computed((): string =>
  activeTab.value === 'journal' ? '' : PROSPECT_SEARCH_EMPTY_TAB_LABELS[activeTab.value],
)

const rejectedGroups: ComputedRef<ProspectSearchRejectedGroup[]> = computed((): ProspectSearchRejectedGroup[] => {
  const groups: ProspectSearchRejectedGroup[] = PROSPECT_SEARCH_REJECT_REASON_ORDER.map(
    (reason: ProspectSearchRejectReason): ProspectSearchRejectedGroup => ({
      key: reason,
      label: PROSPECT_SEARCH_REJECT_REASON_LABELS[reason],
      candidates: candidatesByStatus.value.rejected.filter(
        (candidate: ProspectSearchCandidate): boolean => candidate.reject_reason === reason,
      ),
    }),
  )
  groups.push({
    key: UNEXPLAINED_REJECT_GROUP_KEY,
    label: 'Autre raison',
    candidates: candidatesByStatus.value.rejected.filter(
      (candidate: ProspectSearchCandidate): boolean =>
        candidate.reject_reason === null || !PROSPECT_SEARCH_REJECT_REASON_ORDER.includes(candidate.reject_reason),
    ),
  })
  return groups.filter((group: ProspectSearchRejectedGroup): boolean => group.candidates.length > 0)
})

const tradeLabels: ComputedRef<Record<string, string>> = computed(
  (): Record<string, string> =>
    Object.fromEntries(
      props.search.trade_counts.map((counts: ProspectSearchTradeCounts): [string, string] => [
        counts.trade,
        counts.label,
      ]),
    ),
)

/**
 * Catalog label of the trade a candidate was searched for.
 * @param candidate - The candidate to label.
 * @returns The trade label, or its raw key when the search does not list it.
 */
function tradeLabelOf(candidate: ProspectSearchCandidate): string {
  return tradeLabels.value[candidate.trade] ?? candidate.trade
}

/**
 * Whether the prospect record of a candidate is being fetched.
 * @param candidate - The candidate whose row is drawn.
 * @returns True while its record loads.
 */
function isOpeningProspectOf(candidate: ProspectSearchCandidate): boolean {
  return candidate.prospect_id !== null && candidate.prospect_id === props.openingProspectId
}

/**
 * Show a tab, ignoring a key the row does not offer.
 * @param key - Key of the clicked tab.
 */
function selectTab(key: string): void {
  const tab: ProspectSearchResultTabKey | undefined = PROSPECT_SEARCH_RESULT_TAB_ORDER.find(
    (tabKey: ProspectSearchResultTabKey): boolean => tabKey === key,
  )
  if (tab) activeTab.value = tab
}

/**
 * Unfold a group of discarded candidates, or fold it back.
 * @param groupKey - Key of the clicked group.
 */
function toggleRejectedGroup(groupKey: string): void {
  expandedRejectedGroupKeys.value = expandedRejectedGroupKeys.value.includes(groupKey)
    ? expandedRejectedGroupKeys.value.filter((key: string): boolean => key !== groupKey)
    : [...expandedRejectedGroupKeys.value, groupKey]
}

watch(
  (): number => props.search.id,
  (): void => {
    activeTab.value = DEFAULT_TAB
    expandedRejectedGroupKeys.value = []
  },
)

watch(tabs, (visibleTabs: UiFilterTab[]): void => {
  if (!visibleTabs.some((tab: UiFilterTab): boolean => tab.key === activeTab.value)) activeTab.value = DEFAULT_TAB
})
</script>
