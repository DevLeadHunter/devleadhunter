<template>
  <div
    class="group rounded-xl border border-[#30363d] bg-[#1a1a1a] p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-[#484f58] hover:bg-[#1f1f1f] sm:p-5"
  >
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="text-muted truncate text-xs font-medium tracking-wide uppercase">{{ label }}</p>
        <p class="mt-2 text-2xl font-bold text-[#f9f9f9] tabular-nums sm:text-3xl">{{ value }}</p>
      </div>
      <div
        :class="[
          'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-transform duration-200 group-hover:scale-105',
          tile,
        ]"
      >
        <UIcon :name="icon" :class="['h-5 w-5', iconColor]" />
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

/** Icon tile background classes for the current accent. */
const tile: ComputedRef<string> = computed((): string => {
  const map: Record<UiStatCardAccent, string> = {
    neutral: 'border border-[#30363d] bg-[#050505]',
    emerald: 'bg-[#2BAD5F]/15',
    danger: 'bg-[#DC4747]/15',
    sky: 'bg-[#58a6ff]/15',
  }
  return map[props.accent]
})

/** Icon colour for the current accent. */
const iconColor: ComputedRef<string> = computed((): string => {
  const map: Record<UiStatCardAccent, string> = {
    neutral: 'text-[#f9f9f9]',
    emerald: 'text-[#2BAD5F]',
    danger: 'text-[#DC4747]',
    sky: 'text-[#58a6ff]',
  }
  return map[props.accent]
})
</script>
