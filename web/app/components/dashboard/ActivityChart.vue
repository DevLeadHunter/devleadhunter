<template>
  <div class="relative">
    <!-- Legend -->
    <div class="mb-3 flex items-center gap-4">
      <span class="flex items-center gap-1.5 text-xs text-[var(--app-ink-soft)]">
        <span class="h-2 w-2 rounded-full" style="background-color: #dd9a35"></span> Envoyés
      </span>
      <span class="flex items-center gap-1.5 text-xs text-[var(--app-ink-soft)]">
        <span class="h-2 w-2 rounded-full" style="background-color: #3f8f60"></span> Ouverts
      </span>
    </div>

    <div class="relative" @mouseleave="activeIndex = null">
      <svg :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none" class="h-44 w-full overflow-visible">
        <!-- Horizontal gridlines -->
        <line
          v-for="g in gridLines"
          :key="g.y"
          :x1="0"
          :x2="W"
          :y1="g.y"
          :y2="g.y"
          stroke="currentColor"
          class="text-[var(--app-line)]"
          stroke-width="1"
        />

        <!-- Sent area -->
        <defs>
          <linearGradient id="sentGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#dd9a35" stop-opacity="0.35" />
            <stop offset="100%" stop-color="#dd9a35" stop-opacity="0" />
          </linearGradient>
        </defs>
        <path :d="sentArea" fill="url(#sentGradient)" />
        <path :d="sentLine" fill="none" stroke="#dd9a35" stroke-width="2" vector-effect="non-scaling-stroke" />

        <!-- Opened line -->
        <path :d="openedLine" fill="none" stroke="#3f8f60" stroke-width="2" vector-effect="non-scaling-stroke" />

        <!-- Active guide -->
        <line
          v-if="active"
          :x1="active.x"
          :x2="active.x"
          :y1="0"
          :y2="H"
          stroke="currentColor"
          class="text-[var(--app-ink-soft)]"
          stroke-width="1"
          stroke-dasharray="3 3"
          vector-effect="non-scaling-stroke"
        />
        <circle
          v-if="active"
          :cx="active.x"
          :cy="active.sentY"
          r="3.5"
          fill="#dd9a35"
          vector-effect="non-scaling-stroke"
        />
        <circle
          v-if="active"
          :cx="active.x"
          :cy="active.openedY"
          r="3.5"
          fill="#3f8f60"
          vector-effect="non-scaling-stroke"
        />
      </svg>

      <!-- Hover hit-areas -->
      <div class="absolute inset-0 flex">
        <button
          v-for="(p, i) in points"
          :key="p.date"
          type="button"
          class="h-full flex-1 cursor-default"
          :aria-label="`${formatDay(p.date)} : ${p.sent} envoyés, ${p.opened} ouverts`"
          @mouseenter="activeIndex = i"
          @focus="activeIndex = i"
        />
      </div>

      <!-- Tooltip -->
      <div
        v-if="active"
        class="pointer-events-none absolute z-10 -translate-x-1/2 rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-3 py-2 shadow-xl"
        :style="{ left: `${active.leftPct}%`, top: '0' }"
      >
        <p class="mb-1 text-[11px] font-semibold text-[var(--app-ink)]">{{ formatDay(active.date) }}</p>
        <p class="flex items-center gap-1.5 text-[11px] text-[var(--app-ink-soft)]">
          <span class="h-1.5 w-1.5 rounded-full" style="background-color: #dd9a35"></span>
          {{ active.sent }} envoyés
        </p>
        <p class="flex items-center gap-1.5 text-[11px] text-[var(--app-ink-soft)]">
          <span class="h-1.5 w-1.5 rounded-full" style="background-color: #3f8f60"></span>
          {{ active.opened }} ouverts
        </p>
      </div>
    </div>

    <!-- X axis labels (sparse) -->
    <div class="mt-2 flex justify-between text-[10px] text-[var(--app-ink-soft)]">
      <span>{{ formatDay(points[0]?.date) }}</span>
      <span v-if="midPoint">{{ formatDay(midPoint.date) }}</span>
      <span>{{ formatDay(points[points.length - 1]?.date) }}</span>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'
import type { ActivityPoint } from '~/services/dashboardService'
import type { DashboardActivityChartProps } from '~/types/DashboardActivityChart'

/**
 * Lightweight SVG area + line chart for daily email activity (sent vs opened),
 * with an interactive hover guide and tooltip. No external chart library.
 */
const props: DashboardActivityChartProps = defineProps({
  points: {
    type: Array as () => ActivityPoint[],
    required: true,
  },
})

/** SVG viewBox width. */
const W: number = 600
/** SVG viewBox height. */
const H: number = 160

/** Index of the currently hovered data point. */
const activeIndex: Ref<number | null> = ref<number | null>(null)

/** Maximum value across both series (lower-bounded to 1 to avoid /0). */
const maxValue: ComputedRef<number> = computed((): number => {
  const values: number[] = props.points.flatMap((p: ActivityPoint): number[] => [p.sent, p.opened])
  return Math.max(...values, 1)
})

/**
 * X coordinate for a point index.
 * @param i - Point index.
 * @returns X in viewBox units.
 */
function xAt(i: number): number {
  const n: number = props.points.length
  if (n <= 1) return 0
  return (i / (n - 1)) * W
}

/**
 * Y coordinate for a raw value.
 * @param v - Raw value.
 * @returns Y in viewBox units (top padding included).
 */
function yAt(v: number): number {
  const top: number = 12
  const usable: number = H - top - 6
  return top + usable - (v / maxValue.value) * usable
}

/** SVG path for the "sent" line. */
const sentLine: ComputedRef<string> = computed((): string =>
  props.points
    .map((p: ActivityPoint, i: number): string => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${yAt(p.sent)}`)
    .join(' '),
)

/** SVG path for the filled "sent" area. */
const sentArea: ComputedRef<string> = computed((): string => {
  if (!props.points.length) return ''
  const last: number = props.points.length - 1
  return `${sentLine.value} L ${xAt(last)} ${H} L ${xAt(0)} ${H} Z`
})

/** SVG path for the "opened" line. */
const openedLine: ComputedRef<string> = computed((): string =>
  props.points
    .map((p: ActivityPoint, i: number): string => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${yAt(p.opened)}`)
    .join(' '),
)

/** Three evenly spaced horizontal gridlines. */
const gridLines: ComputedRef<{ y: number }[]> = computed((): { y: number }[] =>
  [0.25, 0.5, 0.75].map((r: number): { y: number } => ({ y: 12 + (H - 18) * r })),
)

/** The middle point used for the central x-axis label. */
const midPoint: ComputedRef<ActivityPoint | null> = computed(
  (): ActivityPoint | null => props.points[Math.floor(props.points.length / 2)] ?? null,
)

/** Resolved active-point geometry and values for the guide and tooltip. */
const active: ComputedRef<{
  x: number
  sentY: number
  openedY: number
  leftPct: number
  date: string
  sent: number
  opened: number
} | null> = computed(() => {
  if (activeIndex.value === null) return null
  const p: ActivityPoint | undefined = props.points[activeIndex.value]
  if (!p) return null
  const n: number = props.points.length
  return {
    x: xAt(activeIndex.value),
    sentY: yAt(p.sent),
    openedY: yAt(p.opened),
    leftPct: n <= 1 ? 50 : (activeIndex.value / (n - 1)) * 100,
    date: p.date,
    sent: p.sent,
    opened: p.opened,
  }
})

/**
 * Format an ISO date (YYYY-MM-DD) as a short French day label.
 * @param iso - ISO date string.
 * @returns Short day label (e.g. "26 mai") or an empty string.
 */
function formatDay(iso: string | undefined): string {
  if (!iso) return ''
  return new Date(`${iso}T00:00:00`).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
}
</script>
