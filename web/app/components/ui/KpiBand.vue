<template>
  <section
    :aria-label="props.label"
    class="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-[var(--app-line)] bg-[var(--app-line)] @3xl:grid-cols-[repeat(var(--kpi-band-columns),minmax(0,1fr))]"
    :style="{ '--kpi-band-columns': props.cells.length }"
  >
    <div
      v-for="(cell, index) in props.cells"
      :key="cell.key"
      class="flex min-w-0 flex-col bg-[var(--app-surface)] px-4 pt-4 @5xl:px-5 @5xl:pt-[18px]"
      :class="{ 'col-span-2 @3xl:col-span-1': index === 0 && props.cells.length % 2 === 1 }"
    >
      <p class="app-label leading-tight @3xl:min-h-[2.6em]">{{ cell.label }}</p>
      <p class="mt-2 text-[30px] leading-none font-medium tracking-[-0.02em] text-[var(--app-ink)] tabular-nums">
        {{ cell.value
        }}<small v-if="cell.total" class="ml-1 text-base font-normal tracking-normal text-[var(--app-ink-soft)]">{{
          cell.total
        }}</small>
      </p>
      <p class="mt-2 text-[12.5px] text-[var(--app-ink)]/80 @3xl:truncate" :title="cell.detail">{{ cell.detail }}</p>
      <div
        class="mt-2 mb-3.5 flex min-h-[22px] flex-wrap items-center gap-x-2 gap-y-1 text-xs text-[var(--app-ink-soft)] @5xl:mb-4"
      >
        <span
          v-if="cell.trendBadge"
          class="inline-flex h-[22px] items-center gap-0.5 rounded-full text-xs font-medium whitespace-nowrap tabular-nums"
          :class="TREND_BADGE_CLASSES[cell.trendBadge.trend]"
        >
          <UIcon :name="TREND_ICONS[cell.trendBadge.trend]" class="h-3.5 w-3.5" />
          {{ cell.trendBadge.text }}
        </span>
        <span v-if="cell.comparisonNote">{{ cell.comparisonNote }}</span>
      </div>
      <span class="-mx-4 mt-auto block h-1 bg-[var(--app-surface-2)] @5xl:-mx-5" aria-hidden="true">
        <span
          class="block h-full"
          :class="METER_TONE_CLASSES[cell.meterTone]"
          :style="{ width: `${Math.round(Math.min(Math.max(cell.meterRatio, 0), 1) * 100)}%` }"
        ></span>
      </span>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { UiKpiBandCell, UiKpiBandMeterTone, UiKpiBandProps, UiKpiBandTrend } from '~/types/UiKpiBand'

const props: UiKpiBandProps = defineProps({
  cells: {
    type: Array as PropType<UiKpiBandCell[]>,
    required: true,
  },
  label: {
    type: String,
    required: true,
  },
})

const TREND_BADGE_CLASSES: Record<UiKpiBandTrend, string> = {
  up: 'bg-[var(--app-green-soft)] pr-2 pl-1.5 text-[var(--app-green)]',
  down: 'bg-[var(--app-red-soft)] pr-2 pl-1.5 text-[var(--app-red)]',
  flat: 'text-[var(--app-ink-soft)]',
}

const TREND_ICONS: Record<UiKpiBandTrend, string> = {
  up: 'i-lucide-arrow-up',
  down: 'i-lucide-arrow-down',
  flat: 'i-lucide-minus',
}

const METER_TONE_CLASSES: Record<UiKpiBandMeterTone, string> = {
  ink: 'bg-[var(--app-ink)]',
  soft: 'bg-[var(--app-faint)]',
  blue: 'bg-[var(--app-blue)]',
  green: 'bg-[var(--app-green)]',
}
</script>
