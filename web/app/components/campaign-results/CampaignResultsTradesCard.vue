<template>
  <section class="app-card flex min-w-0 flex-col" aria-labelledby="campaign-results-trades-title">
    <header class="px-[18px] pt-4">
      <h3 id="campaign-results-trades-title" class="text-[15px] font-medium text-[var(--app-ink)]">Par métier</h3>
      <p class="mt-0.5 text-[13px] text-[var(--app-ink-soft)]">
        Part des prospects qui ont ouvert leur site, un carré par prospect.
      </p>
    </header>

    <ul class="mt-3">
      <li
        v-for="group in props.groups"
        :key="group.key"
        class="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 border-t border-[var(--app-line-soft)] px-[18px] py-[9px] text-[13.5px] first:border-t-0"
      >
        <span class="min-w-0 text-[var(--app-ink)]">
          {{ group.label }} <span class="text-[var(--app-ink-soft)] tabular-nums">{{ group.rows.length }}</span>
        </span>
        <UiUnitChart
          :units="unitsByTrade.get(group.key) ?? []"
          :label="`${group.label} : ${group.visited} sur ${group.contacted} ont ouvert leur site`"
          :unit-size="12"
          class="max-w-[180px]"
          @select="emit('select-prospect', $event)"
        />
        <span class="min-w-11 text-right font-medium text-[var(--app-ink)] tabular-nums">
          {{ group.contacted > 0 ? `${group.visited} / ${group.contacted}` : '—' }}
        </span>
      </li>
    </ul>

    <p v-if="props.note" class="mt-auto px-[18px] pt-3 pb-4 text-[12.5px] leading-snug text-[var(--app-ink-soft)]">
      {{ props.note }}
    </p>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType } from 'vue'
import type { CampaignResultsRow, CampaignResultsTradeGroup } from '~/types/CampaignResults'
import type { CampaignResultsTradesCardEmits, CampaignResultsTradesCardProps } from '~/types/CampaignResultsTradesCard'
import type { UiUnitChartUnit } from '~/types/UiUnitChart'
import { computed } from 'vue'
import { CampaignResults } from '~/utils/campaignResults'

const props: CampaignResultsTradesCardProps = defineProps({
  groups: {
    type: Array as PropType<CampaignResultsTradeGroup[]>,
    required: true,
  },
  note: {
    type: String,
    required: true,
  },
})

const emit: EmitFn<CampaignResultsTradesCardEmits> = defineEmits<CampaignResultsTradesCardEmits>()

const unitsByTrade: ComputedRef<Map<string, UiUnitChartUnit[]>> = computed(
  (): Map<string, UiUnitChartUnit[]> =>
    new Map(
      props.groups.map((group: CampaignResultsTradeGroup): [string, UiUnitChartUnit[]] => [
        group.key,
        group.rows.map((row: CampaignResultsRow): UiUnitChartUnit => CampaignResults.unitOf(row)),
      ]),
    ),
)
</script>
