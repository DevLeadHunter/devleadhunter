<template>
  <div class="flex flex-col items-center text-center">
    <div class="relative h-24 w-24">
      <svg viewBox="0 0 100 100" class="h-full w-full -rotate-90">
        <circle cx="50" cy="50" :r="radius" fill="none" stroke="#21262d" stroke-width="9" />
        <circle
          cx="50"
          cy="50"
          :r="radius"
          fill="none"
          :stroke="hex"
          stroke-width="9"
          stroke-linecap="round"
          :stroke-dasharray="circumference"
          :stroke-dashoffset="dashOffset"
          class="transition-all duration-700 ease-out"
        />
      </svg>
      <div class="absolute inset-0 flex flex-col items-center justify-center">
        <span class="text-xl font-bold text-[#f9f9f9] tabular-nums">{{ clamped }}%</span>
      </div>
    </div>
    <p class="mt-2 text-xs font-medium text-[#c9d1d9]">{{ label }}</p>
    <p v-if="sublabel" class="text-muted text-[11px] tabular-nums">{{ sublabel }}</p>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import { computed } from 'vue'
import type { DashboardRadialRateProps } from '~/types/DashboardRadialRate'
import type { DashboardAccent } from '~/utils/dashboardTheme'
import { accentHex } from '~/utils/dashboardTheme'

/**
 * Circular progress gauge for a single percentage metric (e.g. open rate).
 */
const props: DashboardRadialRateProps = defineProps({
  value: {
    type: Number,
    required: true,
  },
  label: {
    type: String,
    required: true,
  },
  accent: {
    type: String as PropType<DashboardAccent>,
    default: 'blue',
  },
  sublabel: {
    type: String as PropType<string | null>,
    default: null,
  },
})

/** Ring radius in viewBox units. */
const radius: number = 42

/** Ring circumference. */
const circumference: ComputedRef<number> = computed((): number => 2 * Math.PI * radius)

/** Value clamped to the 0–100 range. */
const clamped: ComputedRef<number> = computed((): number => Math.max(0, Math.min(100, Math.round(props.value))))

/** Stroke dash offset corresponding to the clamped value. */
const dashOffset: ComputedRef<number> = computed((): number => circumference.value * (1 - clamped.value / 100))

/** Resolved accent hex color. */
const hex: ComputedRef<string> = computed((): string => accentHex(props.accent))
</script>
