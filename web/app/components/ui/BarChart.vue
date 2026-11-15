<template>
  <section class="rounded-2xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5">
    <h2 class="mb-2.5 text-base font-semibold text-[var(--app-ink)]">{{ props.title }}</h2>
    <ul>
      <li
        v-for="bar in props.bars"
        :key="bar.label"
        class="grid min-h-8.5 grid-cols-[minmax(0,9rem)_minmax(0,1fr)_2.5rem] items-center gap-2.5 text-sm text-[var(--app-ink)]"
      >
        <span class="truncate">{{ bar.label }}</span>
        <span class="block h-2 overflow-hidden rounded-full bg-[var(--app-surface-2)]" aria-hidden="true">
          <span class="block h-2 rounded-full bg-[var(--app-ink)]" :style="{ width: barWidthOf(bar) }"></span>
        </span>
        <span class="text-right font-[family-name:var(--app-font-mono)] text-[13px] tabular-nums">{{ bar.value }}</span>
      </li>
    </ul>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { UiBarChartBar, UiBarChartProps } from '~/types/UiBarChart'
import { computed } from 'vue'

/** Counts as horizontal bars under a title, each as wide as its share of the largest one. */
const props: UiBarChartProps = defineProps({
  title: {
    type: String,
    required: true,
  },
  bars: {
    type: Array as PropType<UiBarChartBar[]>,
    required: true,
  },
})

const largestBarValue: ComputedRef<number> = computed((): number =>
  Math.max(1, ...props.bars.map((bar: UiBarChartBar): number => bar.value)),
)

/**
 * The width of a bar.
 * @param bar - The bar to draw.
 * @returns Its share of the largest bar, as a CSS percentage.
 */
function barWidthOf(bar: UiBarChartBar): string {
  return `${Math.round((bar.value / largestBarValue.value) * 100)}%`
}
</script>
