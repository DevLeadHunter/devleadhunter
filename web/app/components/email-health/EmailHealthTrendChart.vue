<template>
  <div class="relative">
    <!-- Legend -->
    <div class="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1">
      <span
        v-for="serie in series"
        :key="serie.key"
        class="flex items-center gap-1.5 text-xs text-[var(--app-ink-soft)]"
      >
        <span class="h-2 w-2 rounded-full" :style="{ backgroundColor: toneVar(serie.tone) }"></span>
        {{ serie.label }}
      </span>
      <span
        v-for="threshold in thresholds"
        :key="threshold.label"
        class="flex items-center gap-1.5 text-xs text-[var(--app-ink-soft)]"
      >
        <span class="inline-block w-4 border-t border-dashed" :style="{ borderColor: toneVar(threshold.tone) }"></span>
        {{ threshold.label }}
      </span>
    </div>

    <div class="relative" @mouseleave="activeIndex = null">
      <svg :viewBox="`0 0 ${W} ${H}`" class="w-full overflow-visible">
        <!-- Horizontal grid + value labels -->
        <g v-for="grid in gridLines" :key="grid.y">
          <line
            :x1="PAD_LEFT"
            :x2="W"
            :y1="grid.y"
            :y2="grid.y"
            stroke="currentColor"
            class="text-[var(--app-line)]"
            stroke-width="1"
          />
          <text
            :x="PAD_LEFT - 6"
            :y="grid.y + 3"
            text-anchor="end"
            class="fill-[var(--app-faint)] text-[9px] tabular-nums"
          >
            {{ formatAxis(grid.value) }}
          </text>
        </g>

        <!-- Threshold guides -->
        <g v-for="threshold in visibleThresholds" :key="threshold.label">
          <line
            :x1="PAD_LEFT"
            :x2="W"
            :y1="yAt(threshold.value)"
            :y2="yAt(threshold.value)"
            :stroke="toneVar(threshold.tone)"
            stroke-width="1.25"
            stroke-dasharray="5 4"
            opacity="0.8"
          />
        </g>

        <!-- Areas first (under every line) -->
        <template v-for="serie in series" :key="`area-${serie.key}`">
          <defs v-if="serie.area">
            <linearGradient :id="gradientId(serie.key)" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" :stop-color="toneVar(serie.tone)" stop-opacity="0.28" />
              <stop offset="100%" :stop-color="toneVar(serie.tone)" stop-opacity="0" />
            </linearGradient>
          </defs>
          <path v-if="serie.area" :d="areaPath(serie)" :fill="`url(#${gradientId(serie.key)})`" />
        </template>

        <!-- Smooth lines -->
        <path
          v-for="serie in series"
          :key="`line-${serie.key}`"
          :d="linePath(serie)"
          fill="none"
          :stroke="toneVar(serie.tone)"
          stroke-width="2"
          stroke-linecap="round"
        />

        <!-- Hover guide + dots -->
        <g v-if="active">
          <line
            :x1="active.x"
            :x2="active.x"
            :y1="PAD_TOP"
            :y2="H - PAD_BOTTOM"
            stroke="currentColor"
            class="text-[var(--app-ink-soft)]"
            stroke-width="1"
            stroke-dasharray="3 3"
          />
          <circle
            v-for="dot in active.dots"
            :key="dot.key"
            :cx="active.x"
            :cy="dot.y"
            r="3.5"
            :fill="dot.color"
            stroke="var(--app-surface)"
            stroke-width="1.5"
          />
        </g>
      </svg>

      <!-- Hover hit areas -->
      <div class="absolute inset-0 flex" :style="{ paddingLeft: `${(PAD_LEFT / W) * 100}%` }">
        <button
          v-for="(label, index) in labels"
          :key="label"
          type="button"
          tabindex="-1"
          class="h-full flex-1 cursor-default"
          :aria-label="tooltipAria(index)"
          @mouseenter="activeIndex = index"
          @focus="activeIndex = index"
        />
      </div>

      <!-- Tooltip -->
      <div
        v-if="active"
        class="pointer-events-none absolute top-0 z-10 min-w-[130px] rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-3 py-2 shadow-xl"
        :style="tooltipStyle"
      >
        <p class="mb-1 text-[11px] font-semibold text-[var(--app-ink)]">{{ formatDay(active.date) }}</p>
        <p
          v-for="dot in active.dots"
          :key="dot.key"
          class="flex items-center justify-between gap-3 text-[11px] text-[var(--app-ink-soft)]"
        >
          <span class="flex items-center gap-1.5">
            <span class="h-1.5 w-1.5 rounded-full" :style="{ backgroundColor: dot.color }"></span>
            {{ dot.label }}
          </span>
          <span class="font-medium text-[var(--app-ink)] tabular-nums">{{ dot.display }}</span>
        </p>
      </div>
    </div>

    <!-- X axis labels (sparse) -->
    <div
      class="mt-1.5 flex justify-between text-[10px] text-[var(--app-ink-soft)]"
      :style="{ paddingLeft: `${(PAD_LEFT / W) * 100}%` }"
    >
      <span>{{ formatDay(labels[0]) }}</span>
      <span v-if="midLabel">{{ formatDay(midLabel) }}</span>
      <span>{{ formatDay(labels[labels.length - 1]) }}</span>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import { computed, ref, useId } from 'vue'
import type {
  EmailHealthChartSeries,
  EmailHealthChartThreshold,
  EmailHealthChartTone,
  EmailHealthTrendChartProps,
} from '~/types/EmailHealthTrendChart'

/**
 * Smooth multi-series SVG trend chart with threshold guides — theme-aware
 * (every color is an Atelier CSS variable) and dependency-free.
 */
const props: EmailHealthTrendChartProps = defineProps({
  labels: {
    type: Array as PropType<string[]>,
    required: true,
  },
  series: {
    type: Array as PropType<EmailHealthChartSeries[]>,
    required: true,
  },
  thresholds: {
    type: Array as PropType<EmailHealthChartThreshold[]>,
    default: (): EmailHealthChartThreshold[] => [],
  },
  unit: {
    type: String,
    default: '',
  },
})

/** SVG viewBox width. */
const W: number = 640
/** SVG viewBox height. */
const H: number = 210
/** Left padding reserved for the value axis. */
const PAD_LEFT: number = 34
/** Top padding. */
const PAD_TOP: number = 10
/** Bottom padding. */
const PAD_BOTTOM: number = 8

/** Unique id used to namespace the SVG gradients of this instance. */
const uid: string = useId()

/** Index of the hovered point (null = no hover). */
const activeIndex: Ref<number | null> = ref<number | null>(null)

/** Highest plotted value (series + thresholds), raised to a "nice" ceiling. */
const maxValue: ComputedRef<number> = computed((): number => {
  const raw: number = Math.max(
    ...props.series.flatMap((serie: EmailHealthChartSeries): number[] => serie.values),
    ...props.thresholds.map((threshold: EmailHealthChartThreshold): number => threshold.value * 1.25),
    0.0001,
  )
  const magnitude: number = Math.pow(10, Math.floor(Math.log10(raw)))
  const normalized: number = raw / magnitude
  const nice: number = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10
  return nice * magnitude
})

/**
 * Namespaced gradient id for one series.
 * @param key - Series key.
 * @returns A DOM-unique gradient id.
 */
function gradientId(key: string): string {
  return `eh-grad-${uid}-${key}`
}

/**
 * Resolve a tone to its Atelier CSS variable.
 * @param tone - Chart tone.
 * @returns A CSS ``var()`` expression.
 */
function toneVar(tone: EmailHealthChartTone): string {
  const map: Record<EmailHealthChartTone, string> = {
    green: 'var(--app-green)',
    red: 'var(--app-red)',
    amber: 'var(--app-accent)',
    blue: 'var(--app-blue)',
    ink: 'var(--app-ink)',
  }
  return map[tone]
}

/**
 * X coordinate of a point index.
 * @param index - Point index.
 * @returns X in viewBox units.
 */
function xAt(index: number): number {
  const count: number = props.labels.length
  if (count <= 1) return PAD_LEFT
  return PAD_LEFT + (index / (count - 1)) * (W - PAD_LEFT)
}

/**
 * Y coordinate of a raw value.
 * @param value - Raw value.
 * @returns Y in viewBox units, clamped to the plot area.
 */
function yAt(value: number): number {
  const usable: number = H - PAD_TOP - PAD_BOTTOM
  const y: number = PAD_TOP + usable - (value / maxValue.value) * usable
  return Math.max(PAD_TOP, Math.min(H - PAD_BOTTOM, y))
}

/**
 * Catmull-Rom smoothed SVG path through a series' points.
 * @param serie - The series to trace.
 * @returns An SVG path (``M … C …``).
 */
function linePath(serie: EmailHealthChartSeries): string {
  const points: { x: number; y: number }[] = serie.values.map(
    (value: number, index: number): { x: number; y: number } => ({ x: xAt(index), y: yAt(value) }),
  )
  if (points.length === 0) return ''
  if (points.length === 1) return `M ${points[0]!.x} ${points[0]!.y}`

  /**
   * Clamp a control-point Y inside the plot area (kills spline overshoot).
   * @param y - Raw control Y.
   * @returns Clamped Y.
   */
  const clampY = (y: number): number => Math.max(PAD_TOP, Math.min(H - PAD_BOTTOM, y))

  let path: string = `M ${points[0]!.x} ${points[0]!.y}`
  for (let index = 0; index < points.length - 1; index += 1) {
    const previous = points[index - 1] ?? points[index]!
    const current = points[index]!
    const next = points[index + 1]!
    const following = points[index + 2] ?? next
    const control1X: number = current.x + (next.x - previous.x) / 6
    const control1Y: number = clampY(current.y + (next.y - previous.y) / 6)
    const control2X: number = next.x - (following.x - current.x) / 6
    const control2Y: number = clampY(next.y - (following.y - current.y) / 6)
    path += ` C ${control1X} ${control1Y} ${control2X} ${control2Y} ${next.x} ${next.y}`
  }
  return path
}

/**
 * Closed path for a series' gradient area.
 * @param serie - The series to fill.
 * @returns An SVG path closed on the baseline.
 */
function areaPath(serie: EmailHealthChartSeries): string {
  const line: string = linePath(serie)
  if (!line) return ''
  const lastX: number = xAt(serie.values.length - 1)
  const baseline: number = H - PAD_BOTTOM
  return `${line} L ${lastX} ${baseline} L ${PAD_LEFT} ${baseline} Z`
}

/** Grid lines with their axis values. */
const gridLines: ComputedRef<{ y: number; value: number }[]> = computed((): { y: number; value: number }[] =>
  [0.25, 0.5, 0.75, 1].map((ratio: number): { y: number; value: number } => ({
    y: yAt(maxValue.value * ratio),
    value: maxValue.value * ratio,
  })),
)

/** Thresholds that fit inside the current scale. */
const visibleThresholds: ComputedRef<EmailHealthChartThreshold[]> = computed((): EmailHealthChartThreshold[] =>
  props.thresholds.filter((threshold: EmailHealthChartThreshold): boolean => threshold.value <= maxValue.value),
)

/** The middle label used for the central x-axis tick. */
const midLabel: ComputedRef<string | null> = computed(
  (): string | null => props.labels[Math.floor(props.labels.length / 2)] ?? null,
)

/** Geometry + values of the hovered point for the guide and tooltip. */
const active: ComputedRef<{
  x: number
  date: string
  leftPct: number
  dots: { key: string; label: string; y: number; color: string; display: string }[]
} | null> = computed(() => {
  if (activeIndex.value === null) return null
  const date: string | undefined = props.labels[activeIndex.value]
  if (date === undefined) return null
  const index: number = activeIndex.value
  return {
    x: xAt(index),
    date,
    leftPct: (xAt(index) / W) * 100,
    dots: props.series.map((serie: EmailHealthChartSeries) => ({
      key: serie.key,
      label: serie.label,
      y: yAt(serie.values[index] ?? 0),
      color: toneVar(serie.tone),
      display: `${formatValue(serie.values[index] ?? 0)}${props.unit}`,
    })),
  }
})

/** Tooltip position (flips near the right edge). */
const tooltipStyle: ComputedRef<Record<string, string>> = computed((): Record<string, string> => {
  if (!active.value) return {}
  if (active.value.leftPct > 68) {
    return { right: `${100 - active.value.leftPct + 2}%` }
  }
  return { left: `${active.value.leftPct + 2}%` }
})

/**
 * Format a value for the tooltip (2 decimals for rates, integers otherwise).
 * @param value - Raw value.
 * @returns Localized display string.
 */
function formatValue(value: number): string {
  if (props.unit === '%') return value.toLocaleString('fr-FR', { maximumFractionDigits: 2 })
  return Math.round(value).toLocaleString('fr-FR')
}

/**
 * Format an axis tick (compact).
 * @param value - Raw axis value.
 * @returns Short display string.
 */
function formatAxis(value: number): string {
  if (props.unit === '%') return `${value.toLocaleString('fr-FR', { maximumFractionDigits: 1 })}%`
  if (value >= 1000) return `${(value / 1000).toLocaleString('fr-FR', { maximumFractionDigits: 1 })}k`
  return Math.round(value).toLocaleString('fr-FR')
}

/**
 * Accessible summary of one hovered point.
 * @param index - Point index.
 * @returns The aria-label content.
 */
function tooltipAria(index: number): string {
  const parts: string[] = props.series.map(
    (serie: EmailHealthChartSeries): string => `${serie.label} : ${formatValue(serie.values[index] ?? 0)}${props.unit}`,
  )
  return `${formatDay(props.labels[index])} — ${parts.join(', ')}`
}

/**
 * Format an ISO date as a short French label.
 * @param iso - ISO date (YYYY-MM-DD).
 * @returns Localized short date.
 */
function formatDay(iso: string | undefined): string {
  if (!iso) return ''
  return new Date(`${iso}T00:00:00`).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
}
</script>
