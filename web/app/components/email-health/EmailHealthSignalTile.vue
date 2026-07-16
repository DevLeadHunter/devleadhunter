<template>
  <div class="app-card flex flex-col gap-2 p-4">
    <div class="flex items-center justify-between gap-2">
      <p class="app-label">{{ label }}</p>
      <span class="h-2 w-2 shrink-0 rounded-full" :style="{ backgroundColor: statusColor }"></span>
    </div>
    <p class="text-2xl font-bold tabular-nums" :style="{ color: valueColor }">
      {{ value }}<span class="ml-0.5 text-sm font-medium text-[var(--app-ink-soft)]">{{ unit }}</span>
    </p>
    <svg v-if="sparkline.length > 1" :viewBox="`0 0 ${SPARK_W} ${SPARK_H}`" class="h-7 w-full overflow-visible">
      <path :d="sparklinePath" fill="none" :stroke="statusColor" stroke-width="1.5" stroke-linecap="round" />
    </svg>
    <p class="text-[11px] leading-snug text-[var(--app-ink-soft)]">{{ hint }}</p>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import { computed } from 'vue'
import type { EmailHealthSignalStatus, EmailHealthSignalTileProps } from '~/types/EmailHealthSignalTile'

/**
 * One deliverability health signal: label, big value colored by status,
 * a mini sparkline of the daily values and the threshold hint.
 */
const props: EmailHealthSignalTileProps = defineProps({
  label: {
    type: String,
    required: true,
  },
  value: {
    type: String,
    required: true,
  },
  unit: {
    type: String,
    required: true,
  },
  status: {
    type: String as PropType<EmailHealthSignalStatus>,
    required: true,
  },
  hint: {
    type: String,
    required: true,
  },
  sparkline: {
    type: Array as PropType<number[]>,
    default: (): number[] => [],
  },
})

/** Sparkline viewBox width. */
const SPARK_W: number = 120
/** Sparkline viewBox height. */
const SPARK_H: number = 26

/** Status color (green/amber/red Atelier variables). */
const statusColor: ComputedRef<string> = computed((): string => {
  if (props.status === 'ok') return 'var(--app-green)'
  if (props.status === 'warn') return 'var(--app-accent)'
  return 'var(--app-red)'
})

/** Big-value color: only alarming signals get colored, healthy stays ink. */
const valueColor: ComputedRef<string> = computed((): string =>
  props.status === 'ok' ? 'var(--app-ink)' : statusColor.value,
)

/** Smoothed sparkline path over the daily values. */
const sparklinePath: ComputedRef<string> = computed((): string => {
  const values: number[] = props.sparkline
  if (values.length < 2) return ''
  const max: number = Math.max(...values, 0.0001)
  const points: { x: number; y: number }[] = values.map((value: number, index: number): { x: number; y: number } => ({
    x: (index / (values.length - 1)) * SPARK_W,
    y: 2 + (SPARK_H - 4) * (1 - value / max),
  }))
  let path: string = `M ${points[0]!.x} ${points[0]!.y}`
  for (let index = 0; index < points.length - 1; index += 1) {
    const previous = points[index - 1] ?? points[index]!
    const current = points[index]!
    const next = points[index + 1]!
    const following = points[index + 2] ?? next
    path += ` C ${current.x + (next.x - previous.x) / 6} ${current.y + (next.y - previous.y) / 6}`
    path += ` ${next.x - (following.x - current.x) / 6} ${next.y - (following.y - current.y) / 6}`
    path += ` ${next.x} ${next.y}`
  }
  return path
})
</script>
