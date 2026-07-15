<template>
  <div class="app-card group p-4 transition-colors duration-200 hover:border-[var(--app-ink-soft)]">
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="app-label truncate">{{ label }}</p>
        <p class="font-display mt-1.5 text-xl font-semibold text-[var(--app-ink)] tabular-nums sm:text-2xl">
          {{ value }}
        </p>
      </div>
      <div
        class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-transform duration-200 group-hover:scale-105"
        :style="{ backgroundColor: tileBackground }"
      >
        <UIcon :name="icon" class="h-4 w-4" :style="{ color: iconColor }" />
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import { computed } from 'vue'
import type { UiStatCardAccent, UiStatCardProps } from '~/types/UiStatCard'

/**
 * Defines the component props.
 */
const props: UiStatCardProps = defineProps({
  label: {
    type: String,
    required: true,
  },
  value: {
    type: [Number, String] as PropType<number | string>,
    required: true,
  },
  icon: {
    type: String,
    required: true,
  },
  accent: {
    type: String as PropType<UiStatCardAccent>,
    default: 'neutral',
  },
})

/** Icon tile background for the current accent (semantic app palette). */
const tileBackground: ComputedRef<string> = computed((): string => {
  const map: Record<UiStatCardAccent, string> = {
    neutral: 'var(--app-surface-2)',
    emerald: 'var(--app-green-soft)',
    danger: 'var(--app-red-soft)',
    sky: 'var(--app-accent-soft)',
  }
  return map[props.accent]
})

/** Icon colour for the current accent (semantic app palette). */
const iconColor: ComputedRef<string> = computed((): string => {
  const map: Record<UiStatCardAccent, string> = {
    neutral: 'var(--app-ink)',
    emerald: 'var(--app-green)',
    danger: 'var(--app-red)',
    sky: 'var(--app-accent-ink)',
  }
  return map[props.accent]
})
</script>
