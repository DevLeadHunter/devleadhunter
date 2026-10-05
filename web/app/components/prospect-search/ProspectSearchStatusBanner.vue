<template>
  <section class="app-card min-w-0 space-y-3 p-4" aria-labelledby="prospect-search-banner-title">
    <div class="flex flex-col gap-3 @2xl:flex-row @2xl:items-center @2xl:justify-between">
      <div class="min-w-0">
        <div class="flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
          <span :class="['app-badge', status.badgeClass]">
            <UIcon name="i-lucide-loader-circle" class="h-3 w-3 animate-spin" />
            {{ status.label }}
          </span>
          <h2 id="prospect-search-banner-title" class="min-w-0 text-sm font-semibold break-words text-[var(--app-ink)]">
            Recherche : {{ ProspectSearches.tradesLabel(props.search) }}
          </h2>
        </div>
        <p class="mt-1 text-xs leading-relaxed break-words text-[var(--app-ink-soft)]">
          {{ ProspectSearches.objectiveLabel(props.search) }}
        </p>
      </div>
      <div class="grid shrink-0 grid-cols-2 gap-2 @2xl:flex @2xl:items-center">
        <button type="button" class="app-btn-secondary h-9 px-4 text-xs" @click="emit('follow')">
          <UIcon name="i-lucide-panel-right-open" class="h-3.5 w-3.5" />
          Suivre
        </button>
        <button
          type="button"
          class="app-btn-secondary h-9 px-4 text-xs"
          :disabled="props.isCancelling"
          @click="emit('cancel')"
        >
          <UIcon
            :name="props.isCancelling ? 'i-lucide-loader-circle' : 'i-lucide-circle-stop'"
            :class="['h-3.5 w-3.5', props.isCancelling && 'animate-spin']"
          />
          {{ props.isCancelling ? 'Arrêt…' : 'Arrêter' }}
        </button>
      </div>
    </div>

    <ProspectSearchTradeProgressList
      v-if="props.search.trade_counts.length > 0"
      :trade-counts="props.search.trade_counts"
    />

    <p v-if="queuedLabel" class="flex items-start gap-2 text-xs leading-relaxed text-[var(--app-ink-soft)]">
      <UIcon name="i-lucide-list-ordered" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span class="min-w-0 break-words">{{ queuedLabel }}</span>
    </p>

    <p
      v-if="props.latestJournalMessage"
      class="flex items-start gap-2 border-t border-[var(--app-line-soft)] pt-3 text-xs leading-relaxed text-[var(--app-ink-soft)]"
      aria-live="polite"
    >
      <UIcon name="i-lucide-activity" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span class="line-clamp-1 min-w-0 break-words">{{ props.latestJournalMessage }}</span>
    </p>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType } from 'vue'
import type { ProspectSearchSummary } from '~/types/ProspectSearch'
import type {
  ProspectSearchStatusBannerEmits,
  ProspectSearchStatusBannerProps,
} from '~/types/ProspectSearchStatusBanner'
import type { StatusPresentation } from '~/types/StatusPresentation'
import { computed } from 'vue'
import { PROSPECT_SEARCH_STATUS_PRESENTATION } from '~/constants/prospectSearch'
import { ProspectSearches } from '~/utils/prospectSearches'

/** The search running right now, on one card: its status, its objective, each trade's count and its latest step. */
const props: ProspectSearchStatusBannerProps = defineProps({
  search: {
    type: Object as PropType<ProspectSearchSummary>,
    required: true,
  },
  queuedSearches: {
    type: Array as PropType<ProspectSearchSummary[]>,
    default: () => [],
  },
  latestJournalMessage: {
    type: String as PropType<string | null>,
    default: null,
  },
  isCancelling: {
    type: Boolean,
    required: true,
  },
})

const emit: EmitFn<ProspectSearchStatusBannerEmits> = defineEmits<ProspectSearchStatusBannerEmits>()

const status: ComputedRef<StatusPresentation> = computed(
  (): StatusPresentation => PROSPECT_SEARCH_STATUS_PRESENTATION[props.search.status],
)

const queuedLabel: ComputedRef<string | null> = computed((): string | null => {
  const queuedSearches: ProspectSearchSummary[] = props.queuedSearches ?? []
  if (queuedSearches.length === 0) return null
  const searchesInWords: string = queuedSearches
    .map((queued: ProspectSearchSummary): string => ProspectSearches.tradesInWords(queued))
    .join(', puis ')
  return `Ensuite, en file d'attente : ${searchesInWords}.`
})
</script>
