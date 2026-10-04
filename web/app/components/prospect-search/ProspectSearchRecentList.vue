<template>
  <section class="app-card min-w-0 overflow-hidden" aria-labelledby="prospect-search-recent-title">
    <h2 id="prospect-search-recent-title" class="px-4 pt-4 pb-3 text-sm font-semibold text-[var(--app-ink)] @2xl:px-5">
      Recherches récentes
    </h2>
    <ul class="divide-y divide-[var(--app-line-soft)] border-t border-[var(--app-line-soft)]">
      <li v-for="search in visibleSearches" :key="search.id">
        <button
          type="button"
          class="flex w-full cursor-pointer items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-[var(--app-surface-2)]/50 @2xl:px-5"
          :class="
            search.id === props.selectedSearchId
              ? 'bg-[var(--app-surface-2)]/60 shadow-[inset_2px_0_0_var(--app-ink)]'
              : ''
          "
          :aria-current="search.id === props.selectedSearchId ? 'true' : undefined"
          @click="emit('select', search.id)"
        >
          <span class="min-w-0 flex-1">
            <span class="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span class="max-w-full min-w-0 truncate text-sm font-medium text-[var(--app-ink)]">
                {{ ProspectSearches.tradesLabel(search) }}
              </span>
              <span :class="['app-badge', PROSPECT_SEARCH_STATUS_PRESENTATION[search.status].badgeClass]">
                {{ PROSPECT_SEARCH_STATUS_PRESENTATION[search.status].label }}
              </span>
            </span>
            <span class="mt-0.5 block text-xs break-words text-[var(--app-ink-soft)]">
              {{ ProspectSearches.placeLabel(search) }} · {{ formatShortMonthDayTime(search.created_at) }}
            </span>
          </span>
          <span class="font-label shrink-0 text-xs text-[var(--app-ink)] tabular-nums">
            {{ ProspectSearches.keptCount(search) }} / {{ ProspectSearches.wantedCount(search) }}
            <span class="hidden @md:inline">gardés</span>
          </span>
          <UIcon
            :name="search.id === props.loadingSearchId ? 'i-lucide-loader-circle' : 'i-lucide-chevron-right'"
            :class="[
              'h-4 w-4 shrink-0 text-[var(--app-ink-soft)]',
              search.id === props.loadingSearchId && 'animate-spin',
            ]"
          />
        </button>
      </li>
    </ul>
    <button
      v-if="hiddenSearchCount > 0"
      type="button"
      class="flex min-h-[44px] w-full cursor-pointer items-center justify-center gap-1.5 border-t border-[var(--app-line-soft)] px-4 text-xs font-medium text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
      @click="isShowingEverySearch = true"
    >
      {{ hiddenSearchCount > 1 ? `Afficher les ${hiddenSearchCount} autres` : "Afficher l'autre" }}
      <UIcon name="i-lucide-chevron-down" class="h-3.5 w-3.5" />
    </button>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type { ProspectSearchSummary } from '~/types/ProspectSearch'
import type { ProspectSearchRecentListEmits, ProspectSearchRecentListProps } from '~/types/ProspectSearchRecentList'
import { computed, ref } from 'vue'
import { PROSPECT_SEARCH_STATUS_PRESENTATION } from '~/constants/prospectSearch'
import { formatShortMonthDayTime } from '~/utils/date'
import { ProspectSearches } from '~/utils/prospectSearches'

/** The user's recent searches: objective, local date, status and kept count; a click follows the search. */
const props: ProspectSearchRecentListProps = defineProps({
  searches: {
    type: Array as PropType<ProspectSearchSummary[]>,
    required: true,
  },
  selectedSearchId: {
    type: Number as PropType<number | null>,
    default: null,
  },
  loadingSearchId: {
    type: Number as PropType<number | null>,
    default: null,
  },
})

const emit: EmitFn<ProspectSearchRecentListEmits> = defineEmits<ProspectSearchRecentListEmits>()

const SEARCHES_SHOWN_FOLDED: number = 8

const isShowingEverySearch: Ref<boolean> = ref(false)

const visibleSearches: ComputedRef<ProspectSearchSummary[]> = computed((): ProspectSearchSummary[] =>
  isShowingEverySearch.value ? props.searches : props.searches.slice(0, SEARCHES_SHOWN_FOLDED),
)

const hiddenSearchCount: ComputedRef<number> = computed(
  (): number => props.searches.length - visibleSearches.value.length,
)
</script>
