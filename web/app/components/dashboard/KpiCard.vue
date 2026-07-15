<template>
  <component
    :is="to ? NuxtLink : 'div'"
    :to="to || undefined"
    class="group card relative flex flex-col gap-3 overflow-hidden transition-all duration-200"
    :class="to ? 'cursor-pointer hover:-translate-y-0.5 hover:border-[var(--app-ink-soft)]' : ''"
  >
    <!-- Accent glow strip -->
    <span class="absolute inset-x-0 top-0 h-px" :style="{ background: hex }" aria-hidden="true" />

    <div class="flex items-start justify-between gap-3">
      <div
        class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg"
        :style="{ backgroundColor: hexAlpha(hex, 0.12), color: hex }"
      >
        <UIcon :name="icon" class="h-5 w-5" />
      </div>

      <span
        v-if="trend"
        class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold"
        :style="trendStyle"
      >
        <UIcon :name="trendIcon" class="h-3 w-3" />
        {{ trendLabel || '' }}
      </span>
    </div>

    <div>
      <p class="text-muted text-xs font-medium tracking-wide uppercase">{{ label }}</p>
      <p class="mt-1 text-3xl font-bold text-[var(--app-ink)] tabular-nums">{{ value }}</p>
      <p v-if="hint" class="text-muted mt-1 truncate text-xs">{{ hint }}</p>
    </div>
  </component>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import { computed, resolveComponent } from 'vue'
import type { DashboardKpiCardProps, DashboardKpiTrend } from '~/types/DashboardKpiCard'
import type { DashboardAccent } from '~/utils/dashboardTheme'
import { accentHex, hexAlpha } from '~/utils/dashboardTheme'

/**
 * KPI summary card with an accent icon, large value and optional trend chip.
 */
const props: DashboardKpiCardProps = defineProps({
  label: {
    type: String,
    required: true,
  },
  value: {
    type: String,
    required: true,
  },
  icon: {
    type: String,
    required: true,
  },
  accent: {
    type: String as PropType<DashboardAccent>,
    default: 'blue',
  },
  hint: {
    type: String as PropType<string | null>,
    default: null,
  },
  to: {
    type: String as PropType<string | null>,
    default: null,
  },
  trend: {
    type: String as PropType<DashboardKpiTrend | null>,
    default: null,
  },
  trendLabel: {
    type: String as PropType<string | null>,
    default: null,
  },
})

/** NuxtLink component reference for the dynamic root element. */
const NuxtLink = resolveComponent('NuxtLink')

/** Resolved accent hex color. */
const hex: ComputedRef<string> = computed((): string => accentHex(props.accent))

/** Lucide icon for the current trend direction. */
const trendIcon: ComputedRef<string> = computed((): string => {
  if (props.trend === 'up') return 'i-lucide-trending-up'
  if (props.trend === 'down') return 'i-lucide-trending-down'
  return 'i-lucide-minus'
})

/** Inline style (color + tinted background) for the trend chip. */
const trendStyle: ComputedRef<Record<string, string>> = computed((): Record<string, string> => {
  const color: string =
    props.trend === 'down' ? 'var(--app-red)' : props.trend === 'up' ? 'var(--app-green)' : 'var(--app-ink-soft)'
  return { color, backgroundColor: hexAlpha(color, 0.12) }
})
</script>
