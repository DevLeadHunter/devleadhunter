<template>
  <div class="flex flex-col gap-5 @3xl:gap-6">
    <UiLoader v-if="!props.results && props.isLoading" label="Calcul des résultats…" />

    <UiEmptyState
      v-else-if="!props.results"
      title="Résultats indisponibles"
      description="Les chiffres de la campagne n'ont pas pu être calculés. Vérifiez votre connexion et réessayez."
    >
      <template #action>
        <button type="button" class="btn-secondary inline-flex items-center gap-2" @click="emit('retry')">
          <UIcon name="i-lucide-refresh-cw" class="h-4 w-4" />
          Réessayer
        </button>
      </template>
    </UiEmptyState>

    <UiEmptyState
      v-else-if="rows.length === 0"
      title="Pas encore de résultats"
      description="Ajoutez des prospects à la campagne : leurs visites, réponses et ventes s'afficheront ici dès le premier mail."
    />

    <template v-else-if="headline">
      <div class="flex flex-wrap items-end justify-between gap-x-6 gap-y-3.5">
        <div class="min-w-0 flex-[1_1_420px]">
          <p class="app-label">{{ headline.label }}</p>
          <h2
            class="mt-2.5 text-2xl leading-tight font-medium tracking-[-0.015em] text-balance text-[var(--app-ink)] @3xl:text-[28px]"
          >
            {{ headline.title }}
          </h2>
          <p v-if="headline.summary" class="mt-1.5 max-w-[64ch] text-[15px] text-[var(--app-ink)]/80">
            {{ headline.summary }}
          </p>
        </div>
        <div v-if="comparisonOptions.length > 0" class="flex w-full items-center gap-2 @2xl:w-auto">
          <span class="shrink-0 text-[13px] text-[var(--app-ink-soft)]">Comparé à</span>
          <div class="min-w-0 flex-1 @2xl:w-64 @2xl:flex-none">
            <UiSelectField v-model="selectedComparisonKey" :options="comparisonOptions" aria-label="Comparer à" />
          </div>
        </div>
      </div>

      <UiKpiBand :cells="kpiCells" label="Chiffres clés de la campagne" />

      <div class="grid items-start gap-5 @4xl:grid-cols-[minmax(0,1.65fr)_minmax(0,1fr)] @4xl:gap-6">
        <CampaignResultsTodoCard :todos="todos" @act="handleTodoAction" />
        <CampaignResultsStateCard
          :groups="stateGroups"
          :facts="stateFacts"
          :prospect-count="rows.length"
          :is-sending="isSending"
          @select-prospect="emit('open-prospect', $event)"
          @select-state="showProspectsInState"
          @show-prospects="showAllProspects"
          @open-queue="emit('open-queue')"
        />
      </div>

      <CampaignResultsDailyChart
        v-if="hasDailyActivity"
        :days="days"
        :prospect-names="prospectNames"
        :marks="visitMarks"
        :is-visit-tracking-available="props.results.is_visit_tracking_available"
        :period-label="periodLabel"
      />

      <CampaignResultsRepliesCard
        :replies="props.results.replies"
        :rows="rows"
        @open-prospect="emit('open-prospect', $event)"
        @add-reply="openReplyDrawer"
      />

      <div class="grid items-start gap-5 @3xl:gap-6" :class="{ '@3xl:grid-cols-2': tradeGroups.length > 1 }">
        <CampaignResultsTradesCard
          v-if="tradeGroups.length > 1"
          :groups="tradeGroups"
          :note="tradesNote"
          @select-prospect="emit('open-prospect', $event)"
        />
        <CampaignResultsSendsCard
          :steps="stepSummaries"
          :prospect-names="prospectNames"
          :prospect-count="rows.length"
          :note="sendsNote"
          :is-visit-tracking-available="props.results.is_visit_tracking_available"
        />
      </div>

      <CampaignResultsProspectsCard
        ref="prospectsCard"
        v-model:filter="prospectFilter"
        v-model:is-showing-quiet-rows="isShowingQuietRows"
        :rows="rows"
        :days="days"
        :period-label="periodLabel"
        :is-visit-tracking-available="props.results.is_visit_tracking_available"
        @open-prospect="emit('open-prospect', $event)"
      />
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref, WritableComputedRef } from 'vue'
import type { CampaignStatus } from '~/services/campaignService'
import type { CampaignFollowUp } from '~/types'
import type {
  CampaignBenchmark,
  CampaignResultsComparison,
  CampaignResultsDay,
  CampaignResultsFilterKey,
  CampaignResultsHeadline,
  CampaignResultsProspectState,
  CampaignResultsResponse,
  CampaignResultsRow,
  CampaignResultsSend,
  CampaignResultsStateFact,
  CampaignResultsStateGroup,
  CampaignResultsStepSummary,
  CampaignResultsTodo,
  CampaignResultsTodoAction,
  CampaignResultsTradeGroup,
  CampaignResultsVisitMarks,
} from '~/types/CampaignResults'
import type { CampaignResultsProspectsCardExposed } from '~/types/CampaignResultsProspectsCard'
import type { CampaignResultsTabEmits, CampaignResultsTabProps } from '~/types/CampaignResultsTab'
import type { SelectFieldOption } from '~/types/SelectField'
import type { UiKpiBandCell } from '~/types/UiKpiBand'
import { useNow } from '@vueuse/core'
import { computed, ref } from 'vue'
import { CAMPAIGN_RESULTS_FILTER_BY_STATE } from '~/constants/campaignResults'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { CampaignResults } from '~/utils/campaignResults'
import { CampaignResultsSummary } from '~/utils/campaignResultsSummary'

const props: CampaignResultsTabProps = defineProps({
  campaignId: {
    type: Number,
    required: true,
  },
  campaignStatus: {
    type: String as PropType<CampaignStatus>,
    required: true,
  },
  followUps: {
    type: Array as PropType<CampaignFollowUp[]>,
    required: true,
  },
  results: {
    type: Object as PropType<CampaignResultsResponse | null>,
    default: null,
  },
  benchmarks: {
    type: Array as PropType<CampaignBenchmark[]>,
    required: true,
  },
  isLoading: {
    type: Boolean,
    required: true,
  },
})

const emit: EmitFn<CampaignResultsTabEmits> = defineEmits<CampaignResultsTabEmits>()

const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()
const now: Ref<Date> = useNow({ interval: 60_000 })

const prospectsCard: Ref<CampaignResultsProspectsCardExposed | null> = ref(null)
const prospectFilter: Ref<CampaignResultsFilterKey> = ref('all')
const isShowingQuietRows: Ref<boolean> = ref(false)
const comparisonKey: Ref<string> = ref('others')

const rows: ComputedRef<CampaignResultsRow[]> = computed((): CampaignResultsRow[] =>
  props.results ? CampaignResults.buildRows(props.results) : [],
)

const days: ComputedRef<CampaignResultsDay[]> = computed((): CampaignResultsDay[] =>
  props.results ? CampaignResults.buildDays(props.results, now.value) : [],
)

const headline: ComputedRef<CampaignResultsHeadline | null> = computed((): CampaignResultsHeadline | null =>
  props.results ? CampaignResultsSummary.headline(props.results, rows.value, props.campaignStatus, now.value) : null,
)

const comparisons: ComputedRef<CampaignResultsComparison[]> = computed((): CampaignResultsComparison[] =>
  CampaignResults.comparisons(props.benchmarks, props.campaignId),
)

const comparisonOptions: ComputedRef<SelectFieldOption<string>[]> = computed((): SelectFieldOption<string>[] =>
  comparisons.value.map(
    (comparison: CampaignResultsComparison): SelectFieldOption<string> => ({
      value: comparison.key,
      label: comparison.label,
    }),
  ),
)

const selectedComparison: ComputedRef<CampaignResultsComparison | null> = computed(
  (): CampaignResultsComparison | null =>
    comparisons.value.find(
      (comparison: CampaignResultsComparison): boolean => comparison.key === comparisonKey.value,
    ) ??
    comparisons.value[0] ??
    null,
)

const selectedComparisonKey: WritableComputedRef<string> = computed({
  get: (): string => selectedComparison.value?.key ?? '',
  set: (key: string): void => {
    comparisonKey.value = key
  },
})

const kpiCells: ComputedRef<UiKpiBandCell[]> = computed((): UiKpiBandCell[] =>
  props.results ? CampaignResultsSummary.kpiCells(props.results, rows.value, selectedComparison.value, now.value) : [],
)

const todos: ComputedRef<CampaignResultsTodo[]> = computed((): CampaignResultsTodo[] =>
  CampaignResultsSummary.todos(rows.value, now.value),
)

const stateGroups: ComputedRef<CampaignResultsStateGroup[]> = computed((): CampaignResultsStateGroup[] =>
  CampaignResults.stateGroups(rows.value),
)

const stateFacts: ComputedRef<CampaignResultsStateFact[]> = computed((): CampaignResultsStateFact[] =>
  props.results ? CampaignResultsSummary.stateFacts(props.results, rows.value) : [],
)

const isSending: ComputedRef<boolean> = computed((): boolean =>
  props.results ? CampaignResultsSummary.isSending(props.results.totals) : false,
)

const periodLabel: ComputedRef<string> = computed((): string => CampaignResultsSummary.periodLabel(days.value))

const hasDailyActivity: ComputedRef<boolean> = computed((): boolean =>
  days.value.some(
    (day: CampaignResultsDay): boolean =>
      day.visits + day.firstMails + day.followUps + day.plannedFirstMails + day.plannedFollowUps + day.replies.length >
      0,
  ),
)

const visitMarks: ComputedRef<CampaignResultsVisitMarks> = computed(
  (): CampaignResultsVisitMarks => CampaignResults.visitMarks(rows.value),
)

const tradeGroups: ComputedRef<CampaignResultsTradeGroup[]> = computed((): CampaignResultsTradeGroup[] =>
  CampaignResults.tradeGroups(rows.value),
)

const tradesNote: ComputedRef<string> = computed((): string => CampaignResultsSummary.tradesNote(tradeGroups.value))

const stepSummaries: ComputedRef<CampaignResultsStepSummary[]> = computed((): CampaignResultsStepSummary[] => {
  if (!props.results) return []
  const followUpDelays: number[] = [...props.followUps]
    .sort((first: CampaignFollowUp, second: CampaignFollowUp): number => first.position - second.position)
    .map((followUp: CampaignFollowUp): number => followUp.delay_days)
  return CampaignResults.stepSummaries(props.results, rows.value, followUpDelays)
})

const sendsNote: ComputedRef<string> = computed((): string =>
  CampaignResultsSummary.sendsNote(stepSummaries.value, props.results?.replies ?? []),
)

const prospectNames: ComputedRef<Record<number, string>> = computed(
  (): Record<number, string> =>
    Object.fromEntries(
      rows.value.map((row: CampaignResultsRow): [number, string] => [row.prospect.id, row.prospect.name]),
    ),
)

/**
 * Carry out a to-do entry: open the prospect's record, or show the prospects it is about.
 * @param action - The entry's action.
 * @returns A promise resolved once the table is in view.
 */
async function handleTodoAction(action: CampaignResultsTodoAction): Promise<void> {
  if (action.kind === 'prospect') {
    emit('open-prospect', action.prospectId)
    return
  }
  prospectFilter.value = action.filter
  await prospectsCard.value?.reveal(null)
}

/**
 * Show the table filtered on the prospects of a state, from the legend of the state card.
 * @param state - The clicked state.
 * @returns A promise resolved once the table is in view.
 */
async function showProspectsInState(state: CampaignResultsProspectState): Promise<void> {
  prospectFilter.value = CAMPAIGN_RESULTS_FILTER_BY_STATE[state]
  isShowingQuietRows.value = true
  await prospectsCard.value?.reveal(null)
}

/**
 * Show every prospect of the campaign, the quiet ones unfolded.
 * @returns A promise resolved once the table is in view.
 */
async function showAllProspects(): Promise<void> {
  prospectFilter.value = 'all'
  isShowingQuietRows.value = true
  await prospectsCard.value?.reveal(null)
}

/** Open the drawer adding a reply received outside the app, among the prospects a mail reached. */
function openReplyDrawer(): void {
  drawerStack.push({
    kind: 'campaign-reply',
    campaignId: props.campaignId,
    prospects: rows.value
      .filter((row: CampaignResultsRow): boolean =>
        row.prospect.sends.some((send: CampaignResultsSend): boolean => send.status === 'sent'),
      )
      .map(
        (row: CampaignResultsRow): SelectFieldOption<number> => ({ value: row.prospect.id, label: row.prospect.name }),
      )
      .sort((first: SelectFieldOption<number>, second: SelectFieldOption<number>): number =>
        first.label.localeCompare(second.label),
      ),
  })
}
</script>
