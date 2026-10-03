<template>
  <svg
    :viewBox="`0 0 ${CAMPAIGN_RESULTS_JOURNEY_WIDTH} ${AXIS_HEIGHT}`"
    :width="CAMPAIGN_RESULTS_JOURNEY_WIDTH"
    :height="AXIS_HEIGHT"
    aria-hidden="true"
    class="block h-auto w-full max-w-[280px] max-md:max-w-none"
  >
    <text
      v-for="label in dayLabels"
      :key="label.key"
      :x="label.x"
      y="11"
      text-anchor="middle"
      class="font-label text-[9.5px] normal-case"
      :class="{
        'fill-[var(--app-ink)] font-medium': label.isToday,
        'fill-[var(--app-faint)]': !label.isToday && label.isWeekend,
        'fill-[var(--app-ink-soft)]': !label.isToday && !label.isWeekend,
      }"
    >
      {{ label.text }}
    </text>
  </svg>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { CampaignResultsDay } from '~/types/CampaignResults'
import type {
  CampaignResultsJourneyAxisLabel,
  CampaignResultsJourneyAxisProps,
} from '~/types/CampaignResultsJourneyAxis'
import { computed } from 'vue'
import { CAMPAIGN_RESULTS_JOURNEY_WIDTH } from '~/constants/campaignResults'
import { CampaignResultsFormat } from '~/utils/campaignResultsFormat'

const props: CampaignResultsJourneyAxisProps = defineProps({
  days: {
    type: Array as PropType<CampaignResultsDay[]>,
    required: true,
  },
})

const AXIS_HEIGHT: number = 14
const NARROWEST_LABEL_SPACING: number = 16
const DAY_CENTER_RATIO: number = 0.5

const dayLabels: ComputedRef<CampaignResultsJourneyAxisLabel[]> = computed((): CampaignResultsJourneyAxisLabel[] => {
  const bandWidth: number = CAMPAIGN_RESULTS_JOURNEY_WIDTH / Math.max(props.days.length, 1)
  const labelEvery: number = Math.max(1, Math.ceil(NARROWEST_LABEL_SPACING / bandWidth))
  return props.days
    .map(
      (day: CampaignResultsDay, index: number): CampaignResultsJourneyAxisLabel => ({
        key: day.key,
        x: bandWidth * (index + DAY_CENTER_RATIO),
        text: CampaignResultsFormat.dayOfMonth(day.date),
        isToday: day.isToday,
        isWeekend: day.isWeekend,
      }),
    )
    .filter((_: CampaignResultsJourneyAxisLabel, index: number): boolean => index % labelEvery === 0)
})
</script>
