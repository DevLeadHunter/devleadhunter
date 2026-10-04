<template>
  <section class="app-card min-w-0 p-5 @2xl:p-6" aria-labelledby="prospect-search-progress-title">
    <header class="flex flex-col gap-4 @2xl:flex-row @2xl:items-start @2xl:justify-between">
      <div class="min-w-0">
        <div class="flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
          <h2
            id="prospect-search-progress-title"
            class="min-w-0 text-base font-semibold break-words text-[var(--app-ink)]"
          >
            {{ ProspectSearches.tradesLabel(props.search) }}
          </h2>
          <span :class="['app-badge', status.badgeClass]">
            <UIcon v-if="isActive" name="i-lucide-loader-circle" class="h-3 w-3 animate-spin" />
            {{ status.label }}
          </span>
        </div>
        <p class="mt-1.5 text-sm break-words text-[var(--app-ink-soft)]">{{ objectiveLabel }}</p>
        <p class="font-label mt-1.5 text-xs text-[var(--app-ink-soft)]">
          Lancée le {{ formatShortMonthDayTime(props.search.created_at) }} ·
          {{ ProspectSearches.costLabel(props.search.request_count) }}
        </p>
      </div>

      <button
        v-if="isActive"
        type="button"
        class="app-btn-secondary h-9 shrink-0 px-4 text-xs"
        :disabled="props.isCancelling"
        @click="emit('cancel')"
      >
        <UIcon
          :name="props.isCancelling ? 'i-lucide-loader-circle' : 'i-lucide-circle-stop'"
          :class="['h-3.5 w-3.5', props.isCancelling && 'animate-spin']"
        />
        {{ props.isCancelling ? 'Arrêt…' : 'Arrêter' }}
      </button>
      <button
        v-else-if="canResume"
        type="button"
        class="app-btn-primary h-9 shrink-0 px-4 text-xs"
        :disabled="props.isResuming"
        @click="emit('resume')"
      >
        <UIcon
          :name="props.isResuming ? 'i-lucide-loader-circle' : 'i-lucide-play'"
          :class="['h-3.5 w-3.5', props.isResuming && 'animate-spin']"
        />
        Poursuivre
      </button>
    </header>

    <UiCallout v-if="props.search.status === 'failed' && props.search.error_message" variant="danger" class="mt-4">
      {{ props.search.error_message }}
    </UiCallout>

    <ul class="mt-5 space-y-5">
      <li v-for="trade in tradeProgress" :key="trade.key">
        <div class="flex items-baseline justify-between gap-3">
          <span class="min-w-0 truncate text-sm font-medium text-[var(--app-ink)]">{{ trade.label }}</span>
          <span class="font-label shrink-0 text-xs text-[var(--app-ink)] tabular-nums">{{ trade.keptLabel }}</span>
        </div>
        <div
          class="mt-2 h-2 w-full overflow-hidden rounded-full bg-[var(--app-surface-2)]"
          role="progressbar"
          aria-valuemin="0"
          :aria-valuenow="trade.keptCount"
          :aria-valuemax="trade.wantedCount"
          :aria-label="`${trade.label} : ${trade.keptLabel}`"
        >
          <div
            class="h-full rounded-full bg-[var(--app-ink)] transition-[width] duration-300"
            :style="{ width: `${trade.keptPercentage}%` }"
          ></div>
        </div>
        <p class="mt-2 flex flex-wrap gap-x-3.5 gap-y-1 text-xs text-[var(--app-ink-soft)]">
          <span v-for="counterLabel in trade.counterLabels" :key="counterLabel">{{ counterLabel }}</span>
        </p>
        <p
          v-if="trade.stopReasonLabel"
          class="mt-1.5 flex items-start gap-1.5 text-xs leading-relaxed text-[var(--app-accent-ink)]"
        >
          <UIcon name="i-lucide-flag" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
          Objectif non atteint : {{ trade.stopReasonLabel }}.
        </p>
        <p v-if="trade.townsLabel" class="mt-1.5 line-clamp-2 text-xs leading-relaxed text-[var(--app-ink-soft)]">
          Villes parcourues : {{ trade.townsLabel }}
        </p>
      </li>
    </ul>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType } from 'vue'
import type { ProspectSearchSummary, ProspectSearchTradeCounts } from '~/types/ProspectSearch'
import type {
  ProspectSearchProgressCardEmits,
  ProspectSearchProgressCardProps,
  ProspectSearchTradeProgress,
} from '~/types/ProspectSearchProgressCard'
import type { StatusPresentation } from '~/types/StatusPresentation'
import { computed } from 'vue'
import {
  PROSPECT_SEARCH_CHANNEL_OBJECTIVE_LABELS,
  PROSPECT_SEARCH_STATUS_PRESENTATION,
  PROSPECT_SEARCH_STOP_REASON_LABELS,
} from '~/constants/prospectSearch'
import { formatShortMonthDayTime } from '~/utils/date'
import { ProspectSearches } from '~/utils/prospectSearches'

/** The followed search: its objective, its status, how far each trade is from its count, what it cost. */
const props: ProspectSearchProgressCardProps = defineProps({
  search: {
    type: Object as PropType<ProspectSearchSummary>,
    required: true,
  },
  isCancelling: {
    type: Boolean,
    required: true,
  },
  isResuming: {
    type: Boolean,
    required: true,
  },
})

const emit: EmitFn<ProspectSearchProgressCardEmits> = defineEmits<ProspectSearchProgressCardEmits>()

const status: ComputedRef<StatusPresentation> = computed(
  (): StatusPresentation => PROSPECT_SEARCH_STATUS_PRESENTATION[props.search.status],
)

const isActive: ComputedRef<boolean> = computed((): boolean => ProspectSearches.isActive(props.search.status))

const canResume: ComputedRef<boolean> = computed((): boolean => ProspectSearches.canResume(props.search))

const objectiveLabel: ComputedRef<string> = computed((): string => {
  const parts: string[] = [
    `${props.search.count_per_trade} par métier`,
    PROSPECT_SEARCH_CHANNEL_OBJECTIVE_LABELS[props.search.channel],
    ProspectSearches.placeLabel(props.search),
  ]
  if (props.search.only_without_website) parts.push('sans site web')
  if (props.search.minimum_rating !== null) {
    parts.push(`note Google d'au moins ${ProspectSearches.ratingLabel(props.search.minimum_rating)}`)
  }
  return parts.join(' · ')
})

const tradeProgress: ComputedRef<ProspectSearchTradeProgress[]> = computed((): ProspectSearchTradeProgress[] =>
  props.search.trade_counts.map((counts: ProspectSearchTradeCounts): ProspectSearchTradeProgress => {
    const isShortOfObjective: boolean = counts.kept < counts.wanted
    const counterLabels: string[] = [
      `${counts.set_aside} mis de côté`,
      `${counts.to_confirm} à confirmer`,
      `${counts.waiting_browser} ${counts.waiting_browser > 1 ? 'pages' : 'page'} Facebook à lire`,
      `${counts.rejected} ${counts.rejected > 1 ? 'écartés' : 'écarté'}`,
    ]
    if (counts.unverified > 0) {
      counterLabels.push(`${counts.unverified} non ${counts.unverified > 1 ? 'vérifiés' : 'vérifié'}`)
    }
    return {
      key: counts.trade,
      label: counts.label,
      keptLabel: `${counts.kept} / ${counts.wanted} ${counts.kept > 1 ? 'gardés' : 'gardé'}`,
      keptCount: counts.kept,
      wantedCount: counts.wanted,
      keptPercentage: counts.wanted > 0 ? Math.min(100, (counts.kept / counts.wanted) * 100) : 0,
      counterLabels,
      stopReasonLabel:
        counts.stop_reason !== null && isShortOfObjective
          ? PROSPECT_SEARCH_STOP_REASON_LABELS[counts.stop_reason]
          : null,
      townsLabel: counts.towns.length > 0 ? counts.towns.join(', ') : null,
    }
  }),
)
</script>
