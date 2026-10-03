<template>
  <section
    ref="cardElement"
    class="app-card min-w-0 scroll-mt-6 overflow-hidden"
    aria-labelledby="campaign-results-prospects-title"
  >
    <header class="flex flex-wrap items-start gap-x-4 gap-y-3 px-[18px] pt-4">
      <div class="min-w-0 flex-[1_1_220px]">
        <h3 id="campaign-results-prospects-title" class="text-[15px] font-medium text-[var(--app-ink)]">
          {{ props.rows.length > 1 ? `Les ${props.rows.length} prospects` : 'Le prospect' }}
        </h3>
        <p class="mt-0.5 text-[13px] text-[var(--app-ink-soft)]">Un clic ouvre la fiche du prospect.</p>
      </div>
      <div
        class="ml-auto flex flex-wrap items-center gap-x-3.5 gap-y-1 text-[12.5px] text-[var(--app-ink)]/80"
        aria-hidden="true"
      >
        <span class="inline-flex items-center gap-1.5">
          <svg viewBox="0 0 12 12" class="h-3 w-3">
            <rect x="5" y="1" width="2" height="10" rx="1" class="fill-[var(--app-ink)]" />
          </svg>
          Mail
        </span>
        <span v-if="props.isVisitTrackingAvailable" class="inline-flex items-center gap-1.5">
          <svg viewBox="0 0 12 12" class="h-3 w-3">
            <circle cx="6" cy="6" r="4" class="fill-[var(--app-blue)]" />
          </svg>
          Visite
        </span>
        <span class="inline-flex items-center gap-1.5">
          <svg viewBox="0 0 12 12" class="h-3 w-3">
            <rect x="2.5" y="2.5" width="7" height="7" transform="rotate(45 6 6)" class="fill-[var(--app-green)]" />
          </svg>
          Réponse
        </span>
      </div>
    </header>

    <div class="mt-2 flex flex-wrap-reverse items-end gap-x-4 border-b border-[var(--app-line)] px-[18px]">
      <UiFilterTabs v-model="filter" :tabs="filterTabs" class="-ml-4" />
      <div class="relative ml-auto w-full pt-1 pb-3 @3xl:w-60 @3xl:pb-2">
        <UIcon
          name="i-lucide-search"
          class="pointer-events-none absolute top-[22px] left-3 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
        />
        <input
          v-model="searchQuery"
          type="search"
          placeholder="Nom, métier ou ville"
          aria-label="Chercher un prospect"
          autocomplete="off"
          class="app-input h-9 pl-9"
        />
      </div>
    </div>

    <BaseTable v-if="visibleRows.length > 0 || isFoldingQuietRows" min-width="640px" class="max-md:p-3">
      <template #head>
        <BaseTableTh>Prospect</BaseTableTh>
        <BaseTableTh>État</BaseTableTh>
        <BaseTableTh class="min-w-[272px]">
          <span class="sr-only">Parcours {{ props.periodLabel }}</span>
          <CampaignResultsJourneyAxis :days="props.days" />
        </BaseTableTh>
        <BaseTableTh
          v-for="column in sortableColumns"
          :key="column.key"
          align="right"
          :class="{ '@max-4xl:hidden': column.hiddenBelow === '4xl', '@max-5xl:hidden': column.hiddenBelow === '5xl' }"
        >
          <button
            type="button"
            class="inline-flex cursor-pointer items-center gap-1 whitespace-nowrap uppercase transition-colors hover:text-[var(--app-ink)]"
            :class="sortKey === column.key ? 'text-[var(--app-ink)]' : ''"
            @click="toggleSort(column.key)"
          >
            {{ column.label }}
            <UIcon
              :name="sortDirection === 'ascending' ? 'i-lucide-arrow-up' : 'i-lucide-arrow-down'"
              class="h-3 w-3"
              :class="sortKey === column.key ? 'opacity-100' : 'opacity-0'"
            />
          </button>
        </BaseTableTh>
      </template>

      <BaseTableTr
        v-for="row in visibleRows"
        :key="row.prospect.id"
        :data-prospect-id="row.prospect.id"
        tabindex="0"
        class="cursor-pointer"
        :class="
          row.prospect.id === selectedProspectId
            ? 'bg-[var(--app-surface-2)]/60 shadow-[inset_2px_0_0_var(--app-ink)]'
            : ''
        "
        @click="openProspect(row.prospect.id)"
        @keydown.enter="openProspect(row.prospect.id)"
      >
        <BaseTableTd class="min-w-[11rem]">
          <span class="block text-sm font-medium text-[var(--app-ink)]">{{ row.prospect.name }}</span>
          <span class="mt-px block text-[12.5px] text-[var(--app-ink-soft)]">
            {{ row.prospect.category }}{{ row.prospect.city ? ` · ${row.prospect.city}` : '' }}
          </span>
        </BaseTableTd>
        <BaseTableTd label="État">
          <span
            class="inline-flex items-center gap-[7px] text-[13px] whitespace-nowrap"
            :class="CAMPAIGN_RESULTS_STATE_TEXT_CLASSES[row.prospect.state]"
          >
            <span
              class="h-[7px] w-[7px] shrink-0 rounded-full"
              :class="
                row.prospect.state === 'pending' || row.prospect.state === 'not_sent'
                  ? 'border border-[var(--app-faint)]'
                  : 'bg-current'
              "
            ></span>
            {{ CAMPAIGN_RESULTS_STATE_LABELS[row.prospect.state] }}
          </span>
        </BaseTableTd>
        <BaseTableTd class="min-w-[272px]">
          <CampaignResultsJourney :row="row" :days="props.days" />
          <CampaignResultsJourneyAxis :days="props.days" class="mt-1 md:hidden" />
        </BaseTableTd>
        <BaseTableTd
          v-if="props.isVisitTrackingAvailable"
          label="Visites"
          align="right"
          class="text-sm text-[var(--app-ink)] tabular-nums"
        >
          <template v-if="row.visitCount > 0">{{ row.visitCount }}</template>
          <span v-else class="text-[var(--app-ink-soft)]">—</span>
        </BaseTableTd>
        <BaseTableTd
          v-if="props.isVisitTrackingAvailable"
          label="Temps actif"
          align="right"
          class="text-sm text-[var(--app-ink)] tabular-nums @max-4xl:hidden"
        >
          <template v-if="row.activeSeconds > 0">{{ CampaignResultsFormat.activeTime(row.activeSeconds) }}</template>
          <span v-else class="text-[var(--app-ink-soft)]">—</span>
        </BaseTableTd>
        <BaseTableTd
          v-if="props.isVisitTrackingAvailable"
          label="Dernière visite"
          align="right"
          class="text-sm whitespace-nowrap text-[var(--app-ink)] tabular-nums @max-5xl:hidden"
        >
          <template v-if="row.lastVisitAt">
            {{ CampaignResultsFormat.numericDay(row.lastVisitAt) }} · {{ CampaignResultsFormat.clock(row.lastVisitAt) }}
          </template>
          <span v-else class="text-[var(--app-ink-soft)]">—</span>
        </BaseTableTd>
      </BaseTableTr>

      <BaseTableTr v-if="isFoldingQuietRows">
        <td :colspan="props.isVisitTrackingAvailable ? 6 : 3" class="p-0">
          <button
            type="button"
            class="flex min-h-[46px] w-full cursor-pointer items-center justify-center gap-1.5 px-[18px] text-[13px] font-medium text-[var(--app-ink)]/80 transition-colors hover:text-[var(--app-ink)]"
            @click="isShowingQuietRows = true"
          >
            {{ foldLabel }}
            <UIcon name="i-lucide-chevron-down" class="h-[15px] w-[15px]" />
          </button>
        </td>
      </BaseTableTr>
    </BaseTable>

    <p v-else class="px-[18px] py-7 text-center text-[13.5px] text-[var(--app-ink-soft)]">
      Aucun prospect ne correspond à cette recherche.
    </p>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, ModelRef, PropType, Ref } from 'vue'
import type {
  CampaignResultsDay,
  CampaignResultsFilterKey,
  CampaignResultsRow,
  CampaignResultsSortDirection,
  CampaignResultsSortKey,
} from '~/types/CampaignResults'
import type {
  CampaignResultsProspectsCardEmits,
  CampaignResultsProspectsCardExposed,
  CampaignResultsProspectsCardProps,
  CampaignResultsSortableColumn,
} from '~/types/CampaignResultsProspectsCard'
import type { UiFilterTab } from '~/types/UiFilterTabs'
import { computed, nextTick, ref } from 'vue'
import {
  CAMPAIGN_RESULTS_FILTER_LABELS,
  CAMPAIGN_RESULTS_STATE_LABELS,
  CAMPAIGN_RESULTS_STATE_TEXT_CLASSES,
} from '~/constants/campaignResults'
import { CampaignResults } from '~/utils/campaignResults'
import { CampaignResultsFormat } from '~/utils/campaignResultsFormat'

const filter: ModelRef<CampaignResultsFilterKey> = defineModel<CampaignResultsFilterKey>('filter', { required: true })

const isShowingQuietRows: ModelRef<boolean> = defineModel<boolean>('isShowingQuietRows', { required: true })

const props: CampaignResultsProspectsCardProps = defineProps({
  rows: {
    type: Array as PropType<CampaignResultsRow[]>,
    required: true,
  },
  days: {
    type: Array as PropType<CampaignResultsDay[]>,
    required: true,
  },
  periodLabel: {
    type: String,
    required: true,
  },
  isVisitTrackingAvailable: {
    type: Boolean,
    required: true,
  },
})

const emit: EmitFn<CampaignResultsProspectsCardEmits> = defineEmits<CampaignResultsProspectsCardEmits>()

const FILTER_ORDER: CampaignResultsFilterKey[] = ['all', 'opened', 'toRelaunch', 'replied', 'silent', 'pending']
const QUIET_ROWS_KEPT_UNFOLDED: number = 4

const cardElement: Ref<HTMLElement | null> = ref(null)
const searchQuery: Ref<string> = ref('')
const sortKey: Ref<CampaignResultsSortKey> = ref('default')
const sortDirection: Ref<CampaignResultsSortDirection> = ref('descending')
const selectedProspectId: Ref<number | null> = ref(null)

const sortableColumns: ComputedRef<CampaignResultsSortableColumn[]> = computed((): CampaignResultsSortableColumn[] =>
  props.isVisitTrackingAvailable
    ? [
        { key: 'visits', label: 'Visites', hiddenBelow: null },
        { key: 'activeTime', label: 'Temps actif', hiddenBelow: '4xl' },
        { key: 'lastVisit', label: 'Dernière visite', hiddenBelow: '5xl' },
      ]
    : [],
)

const filterTabs: ComputedRef<UiFilterTab[]> = computed((): UiFilterTab[] =>
  FILTER_ORDER.map(
    (key: CampaignResultsFilterKey): UiFilterTab => ({
      key,
      label: CAMPAIGN_RESULTS_FILTER_LABELS[key],
      count: props.rows.filter((row: CampaignResultsRow): boolean => CampaignResults.matchesFilter(row, key)).length,
    }),
  ).filter((tab: UiFilterTab): boolean => tab.key !== 'pending' || (tab.count ?? 0) > 0),
)

const matchingRows: ComputedRef<CampaignResultsRow[]> = computed((): CampaignResultsRow[] => {
  const foldedQuery: string = CampaignResults.foldForSearch(searchQuery.value.trim())
  const rows: CampaignResultsRow[] = props.rows.filter(
    (row: CampaignResultsRow): boolean =>
      CampaignResults.matchesFilter(row, filter.value) && CampaignResults.matchesSearch(row, foldedQuery),
  )
  return CampaignResults.sortRows(rows, sortKey.value, sortDirection.value)
})

const quietRows: ComputedRef<CampaignResultsRow[]> = computed((): CampaignResultsRow[] =>
  matchingRows.value.filter((row: CampaignResultsRow): boolean => CampaignResults.isQuietRow(row)),
)

const isFoldingQuietRows: ComputedRef<boolean> = computed(
  (): boolean =>
    filter.value === 'all' &&
    sortKey.value === 'default' &&
    searchQuery.value.trim() === '' &&
    !isShowingQuietRows.value &&
    quietRows.value.length > QUIET_ROWS_KEPT_UNFOLDED &&
    quietRows.value.length < matchingRows.value.length,
)

const visibleRows: ComputedRef<CampaignResultsRow[]> = computed((): CampaignResultsRow[] =>
  isFoldingQuietRows.value
    ? matchingRows.value.filter((row: CampaignResultsRow): boolean => !CampaignResults.isQuietRow(row))
    : matchingRows.value,
)

const foldLabel: ComputedRef<string> = computed((): string => {
  const hasUncontacted: boolean = quietRows.value.some(
    (row: CampaignResultsRow): boolean => row.prospect.state !== 'silent',
  )
  const hasSilent: boolean = quietRows.value.some((row: CampaignResultsRow): boolean => row.prospect.state === 'silent')
  return `Afficher les ${quietRows.value.length} autres, ${quietRowsKindLabel(hasSilent, hasUncontacted)}`
})

/**
 * What the folded prospects have in common.
 * @param hasSilent - Some of them got mails without reacting.
 * @param hasUncontacted - Some of them got no mail yet.
 * @returns « sans réaction », « pas encore contactés », or both.
 */
function quietRowsKindLabel(hasSilent: boolean, hasUncontacted: boolean): string {
  if (hasSilent && hasUncontacted) return 'sans réaction ou pas encore contactés'
  if (hasSilent) return 'sans réaction'
  return 'pas encore contactés'
}

/**
 * Sort by a column, or flip the direction when it already sorts the table.
 * @param key - The clicked column.
 */
function toggleSort(key: CampaignResultsSortKey): void {
  if (sortKey.value === key) {
    sortDirection.value = sortDirection.value === 'descending' ? 'ascending' : 'descending'
    return
  }
  sortKey.value = key
  sortDirection.value = 'descending'
}

/**
 * Mark a prospect's row and ask for its record.
 * @param prospectId - The prospect.
 */
function openProspect(prospectId: number): void {
  selectedProspectId.value = prospectId
  emit('open-prospect', prospectId)
}

/**
 * Bring the table into view, scrolled to a prospect's row when one is given.
 * @param prospectId - The prospect to show, null for the top of the table.
 * @returns A promise resolved once the scroll started.
 */
async function reveal(prospectId: number | null): Promise<void> {
  selectedProspectId.value = prospectId
  await nextTick()
  const row: Element | null | undefined =
    prospectId === null ? null : cardElement.value?.querySelector(`[data-prospect-id="${prospectId}"]`)
  if (row) {
    row.scrollIntoView({ behavior: 'smooth', block: 'center' })
    return
  }
  cardElement.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const exposed: CampaignResultsProspectsCardExposed = { reveal }

defineExpose(exposed)
</script>
