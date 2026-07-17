<template>
  <div class="relative">
    <!-- Legend: each encoding is visually distinct so the reading is immediate -->
    <div class="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1">
      <span class="flex items-center gap-1.5 text-xs text-[var(--app-ink-soft)]">
        <span class="h-3 w-2.5 rounded-[2px] border border-[var(--app-ink-soft)] bg-[var(--app-ink)]/15"></span>
        Envoyés
      </span>
      <span class="flex items-center gap-1.5 text-xs text-[var(--app-ink-soft)]">
        <span class="h-3 w-2.5 rounded-[2px]" style="background-color: var(--app-green)"></span>
        Délivrés
      </span>
      <span class="flex items-center gap-1.5 text-xs text-[var(--app-ink-soft)]">
        <span class="relative inline-block h-[2.5px] w-5" style="background-color: var(--app-ink)">
          <span
            class="absolute top-1/2 left-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--app-surface)]"
            style="background-color: var(--app-ink)"
          ></span>
        </span>
        Ouverts
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

        <!-- Daily bars: outlined ink column = sent, green filled portion = delivered -->
        <g v-for="(bar, index) in bars" :key="labels[index] ?? index">
          <rect
            v-if="bar.sentHeight > 0"
            :x="bar.x"
            :y="baseline - bar.sentHeight"
            :width="bar.width"
            :height="bar.sentHeight"
            rx="2"
            fill="var(--app-ink)"
            fill-opacity="0.14"
            stroke="var(--app-ink-soft)"
            stroke-width="1"
          />
          <rect
            v-if="bar.deliveredHeight > 0"
            :x="bar.x"
            :y="baseline - bar.deliveredHeight"
            :width="bar.width"
            :height="bar.deliveredHeight"
            rx="2"
            fill="var(--app-green)"
            :opacity="activeIndex === null || activeIndex === index ? 1 : 0.5"
          />
        </g>

        <!-- Opened: bold ink line with big dots — maximum contrast on both themes -->
        <path :d="openedPath" fill="none" stroke="var(--app-ink)" stroke-width="2.5" stroke-linecap="round" />
        <circle
          v-for="dot in openedDots"
          :key="dot.x"
          :cx="dot.x"
          :cy="dot.y"
          r="3.5"
          fill="var(--app-ink)"
          stroke="var(--app-surface)"
          stroke-width="1.5"
        />

        <!-- Hover guide -->
        <line
          v-if="active"
          :x1="active.center"
          :x2="active.center"
          :y1="PAD_TOP"
          :y2="baseline"
          stroke="currentColor"
          class="text-[var(--app-ink-soft)]"
          stroke-width="1"
          stroke-dasharray="3 3"
        />
      </svg>

      <!-- Hover hit areas -->
      <div class="absolute inset-0 flex" :style="{ paddingLeft: `${(PAD_LEFT / W) * 100}%` }">
        <button
          v-for="(label, index) in labels"
          :key="label"
          type="button"
          tabindex="-1"
          class="h-full flex-1 cursor-default"
          :aria-label="ariaFor(index)"
          @mouseenter="activeIndex = index"
          @focus="activeIndex = index"
        />
      </div>

      <!-- Tooltip -->
      <div
        v-if="active"
        class="pointer-events-none absolute top-0 z-10 min-w-[140px] rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-3 py-2 shadow-xl"
        :style="tooltipStyle"
      >
        <p class="mb-1 text-[11px] font-semibold text-[var(--app-ink)]">{{ formatDay(active.date) }}</p>
        <p class="flex items-center justify-between gap-3 text-[11px] text-[var(--app-ink-soft)]">
          <span>Envoyés</span>
          <span class="font-medium text-[var(--app-ink)] tabular-nums">{{ active.sent }}</span>
        </p>
        <p class="flex items-center justify-between gap-3 text-[11px] text-[var(--app-ink-soft)]">
          <span class="flex items-center gap-1.5">
            <span class="h-1.5 w-1.5 rounded-full" style="background-color: var(--app-green)"></span> Délivrés
          </span>
          <span class="font-medium text-[var(--app-ink)] tabular-nums">
            {{ active.delivered }}
            <span v-if="active.sent > 0" class="text-[var(--app-ink-soft)]">({{ active.deliveredPct }}%)</span>
          </span>
        </p>
        <p class="flex items-center justify-between gap-3 text-[11px] text-[var(--app-ink-soft)]">
          <span class="flex items-center gap-1.5">
            <span class="h-1.5 w-1.5 rounded-full" style="background-color: var(--app-ink)"></span> Ouverts
          </span>
          <span class="font-medium text-[var(--app-ink)] tabular-nums">{{ active.opened }}</span>
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
import { computed, ref } from 'vue'
import type { EmailHealthVolumeChartProps } from '~/types/EmailHealthVolumeChart'

/**
 * Daily sending-volume chart designed for readability at any density:
 * outlined ink columns = sent, their green-filled portion = delivered (the
 * visible cap is exactly the non-delivered part), bold ink dotted line = opened.
 */
const props: EmailHealthVolumeChartProps = defineProps({
  labels: {
    type: Array as PropType<string[]>,
    required: true,
  },
  sent: {
    type: Array as PropType<number[]>,
    required: true,
  },
  delivered: {
    type: Array as PropType<number[]>,
    required: true,
  },
  opened: {
    type: Array as PropType<number[]>,
    required: true,
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

/** Index of the hovered day (null = no hover). */
const activeIndex: Ref<number | null> = ref<number | null>(null)

/** Y coordinate of the bars' baseline. */
const baseline: number = H - PAD_BOTTOM

/** Highest daily "sent" count, raised to a nice ceiling. */
const maxValue: ComputedRef<number> = computed((): number => {
  const raw: number = Math.max(...props.sent, ...props.opened, 1)
  const magnitude: number = Math.pow(10, Math.floor(Math.log10(raw)))
  const normalized: number = raw / magnitude
  const nice: number = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10
  return nice * magnitude
})

/** Plot width available for the bars. */
const plotWidth: number = W - PAD_LEFT

/**
 * Height in viewBox units for a raw count.
 * @param value - Raw count.
 * @returns Bar height.
 */
function heightFor(value: number): number {
  return (value / maxValue.value) * (baseline - PAD_TOP)
}

/**
 * Center X of a day's slot.
 * @param index - Day index.
 * @returns X in viewBox units.
 */
function centerAt(index: number): number {
  const count: number = Math.max(props.labels.length, 1)
  return PAD_LEFT + ((index + 0.5) / count) * plotWidth
}

/** Bar geometry for every day. */
const bars: ComputedRef<{ x: number; width: number; sentHeight: number; deliveredHeight: number }[]> = computed(
  (): { x: number; width: number; sentHeight: number; deliveredHeight: number }[] => {
    const count: number = Math.max(props.labels.length, 1)
    const slot: number = plotWidth / count
    const width: number = Math.max(Math.min(slot * 0.7, 26), 2)
    return props.labels.map((_: string, index: number) => ({
      x: centerAt(index) - width / 2,
      width,
      sentHeight: heightFor(props.sent[index] ?? 0),
      deliveredHeight: heightFor(props.delivered[index] ?? 0),
    }))
  },
)

/** Straight-segment path of the opened line (dots carry the emphasis). */
const openedPath: ComputedRef<string> = computed((): string =>
  props.opened
    .map(
      (value: number, index: number): string =>
        `${index === 0 ? 'M' : 'L'} ${centerAt(index)} ${baseline - heightFor(value)}`,
    )
    .join(' '),
)

/** Dot positions of the opened line (skipped on zero-send days to reduce noise). */
const openedDots: ComputedRef<{ x: number; y: number }[]> = computed((): { x: number; y: number }[] =>
  props.opened
    .map((value: number, index: number): { x: number; y: number; show: boolean } => ({
      x: centerAt(index),
      y: baseline - heightFor(value),
      show: (props.sent[index] ?? 0) > 0,
    }))
    .filter((dot: { x: number; y: number; show: boolean }): boolean => dot.show)
    .map((dot: { x: number; y: number; show: boolean }): { x: number; y: number } => ({ x: dot.x, y: dot.y })),
)

/** Grid lines with their axis values. */
const gridLines: ComputedRef<{ y: number; value: number }[]> = computed((): { y: number; value: number }[] =>
  [0.25, 0.5, 0.75, 1].map((ratio: number): { y: number; value: number } => ({
    y: baseline - (baseline - PAD_TOP) * ratio,
    value: maxValue.value * ratio,
  })),
)

/** The middle label used for the central x-axis tick. */
const midLabel: ComputedRef<string | null> = computed(
  (): string | null => props.labels[Math.floor(props.labels.length / 2)] ?? null,
)

/** Values + geometry of the hovered day. */
const active: ComputedRef<{
  center: number
  date: string
  sent: number
  delivered: number
  deliveredPct: number
  opened: number
  leftPct: number
} | null> = computed(() => {
  if (activeIndex.value === null) return null
  const date: string | undefined = props.labels[activeIndex.value]
  if (date === undefined) return null
  const index: number = activeIndex.value
  const sent: number = props.sent[index] ?? 0
  const delivered: number = props.delivered[index] ?? 0
  return {
    center: centerAt(index),
    date,
    sent,
    delivered,
    deliveredPct: sent > 0 ? Math.round((delivered / sent) * 100) : 0,
    opened: props.opened[index] ?? 0,
    leftPct: (centerAt(index) / W) * 100,
  }
})

/** Tooltip position (flips near the right edge). */
const tooltipStyle: ComputedRef<Record<string, string>> = computed((): Record<string, string> => {
  if (!active.value) return {}
  if (active.value.leftPct > 66) {
    return { right: `${100 - active.value.leftPct + 2}%` }
  }
  return { left: `${active.value.leftPct + 2}%` }
})

/**
 * Format an axis tick (compact).
 * @param value - Raw axis value.
 * @returns Short display string.
 */
function formatAxis(value: number): string {
  if (value >= 1000) return `${(value / 1000).toLocaleString('fr-FR', { maximumFractionDigits: 1 })}k`
  return Math.round(value).toLocaleString('fr-FR')
}

/**
 * Accessible summary of one day.
 * @param index - Day index.
 * @returns The aria-label content.
 */
function ariaFor(index: number): string {
  return `${formatDay(props.labels[index])} : ${props.sent[index] ?? 0} envoyés, ${
    props.delivered[index] ?? 0
  } délivrés, ${props.opened[index] ?? 0} ouverts`
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
