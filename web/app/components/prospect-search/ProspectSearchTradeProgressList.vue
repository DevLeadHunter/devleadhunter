<template>
  <ul :class="props.shouldShowDetails ? 'space-y-4' : 'grid gap-x-6 gap-y-2.5 @2xl:grid-cols-2 @5xl:grid-cols-3'">
    <li v-for="trade in tradeProgress" :key="trade.key" class="min-w-0">
      <div class="flex items-baseline justify-between gap-3">
        <span class="min-w-0 truncate text-xs font-medium text-[var(--app-ink)]">{{ trade.label }}</span>
        <span class="font-label shrink-0 text-xs text-[var(--app-ink)] tabular-nums">
          {{ trade.foundCount }} / {{ trade.wantedCount }}
        </span>
      </div>
      <div
        class="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-[var(--app-surface-2)]"
        role="progressbar"
        aria-valuemin="0"
        :aria-valuenow="trade.foundCount"
        :aria-valuemax="trade.wantedCount"
        :aria-label="`${trade.label} : ${trade.foundCount} sur ${trade.wantedCount}`"
      >
        <div
          class="h-full rounded-full bg-[var(--app-ink)] transition-[width] duration-300"
          :style="{ width: `${trade.foundPercentage}%` }"
        ></div>
      </div>
      <template v-if="props.shouldShowDetails">
        <p
          v-if="trade.counterLabels.length > 0"
          class="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-[var(--app-ink-soft)]"
        >
          <span v-for="counterLabel in trade.counterLabels" :key="counterLabel">{{ counterLabel }}</span>
        </p>
        <p
          v-if="trade.stopReasonLabel"
          class="mt-1 flex items-start gap-1.5 text-[11px] leading-relaxed text-[var(--app-accent-ink)]"
        >
          <UIcon name="i-lucide-flag" class="mt-0.5 h-3 w-3 shrink-0" />
          Objectif non atteint : {{ trade.stopReasonLabel }}.
        </p>
        <p v-if="trade.townsLabel" class="mt-1 line-clamp-2 text-[11px] leading-relaxed text-[var(--app-ink-soft)]">
          Villes parcourues : {{ trade.townsLabel }}
        </p>
      </template>
    </li>
  </ul>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { ProspectSearchTradeCounts } from '~/types/ProspectSearch'
import type {
  ProspectSearchTradeProgress,
  ProspectSearchTradeProgressListProps,
} from '~/types/ProspectSearchTradeProgressList'
import { computed } from 'vue'
import { PROSPECT_SEARCH_STOP_REASON_LABELS } from '~/constants/prospectSearch'

/** How far each trade of a search is from its count, with its counters, stop reason and towns when asked. */
const props: ProspectSearchTradeProgressListProps = defineProps({
  tradeCounts: {
    type: Array as PropType<ProspectSearchTradeCounts[]>,
    required: true,
  },
  shouldShowDetails: {
    type: Boolean,
    default: false,
  },
})

const tradeProgress: ComputedRef<ProspectSearchTradeProgress[]> = computed((): ProspectSearchTradeProgress[] =>
  props.tradeCounts.map((counts: ProspectSearchTradeCounts): ProspectSearchTradeProgress => {
    const counters: [number, string][] = [
      [counts.set_aside, `${counts.set_aside} avec un seul contact`],
      [counts.to_confirm, `${counts.to_confirm} à vérifier`],
      [
        counts.waiting_browser,
        `${counts.waiting_browser} ${counts.waiting_browser > 1 ? 'pages' : 'page'} Facebook à lire`,
      ],
      [counts.rejected, `${counts.rejected} ${counts.rejected > 1 ? 'écartés' : 'écarté'}`],
      [counts.unverified, `${counts.unverified} non ${counts.unverified > 1 ? 'vérifiés' : 'vérifié'}`],
    ]
    return {
      key: counts.trade,
      label: counts.label,
      foundCount: counts.kept,
      wantedCount: counts.wanted,
      foundPercentage: counts.wanted > 0 ? Math.min(100, (counts.kept / counts.wanted) * 100) : 0,
      counterLabels: counters
        .filter(([count]: [number, string]): boolean => count > 0)
        .map(([, label]: [number, string]): string => label),
      stopReasonLabel:
        counts.stop_reason !== null && counts.kept < counts.wanted
          ? PROSPECT_SEARCH_STOP_REASON_LABELS[counts.stop_reason]
          : null,
      townsLabel: counts.towns.length > 0 ? counts.towns.join(', ') : null,
    }
  }),
)
</script>
