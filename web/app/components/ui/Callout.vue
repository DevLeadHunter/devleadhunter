<template>
  <div
    class="flex items-start gap-2.5 rounded-lg border px-3 py-2.5"
    :style="{ borderColor: style.border, backgroundColor: style.bg }"
  >
    <UIcon :name="icon ?? style.icon" class="mt-0.5 h-3.5 w-3.5 shrink-0" :style="{ color: style.accent }" />
    <div class="text-xs leading-relaxed text-[var(--app-ink-soft)]">
      <slot />
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import { computed } from 'vue'
import type { UiCalloutProps, UiCalloutVariant } from '~/types/UiCallout'

/** Resolved colours of a callout variant. */
interface CalloutStyle {
  icon: string
  accent: string
  bg: string
  border: string
}

/**
 * Defines the component props.
 */
const props: UiCalloutProps = defineProps({
  variant: {
    type: String as PropType<UiCalloutVariant>,
    default: 'info',
  },
  icon: {
    type: String,
    default: undefined,
  },
})

/** Per-variant colour tokens (theme-aware via CSS variables). */
const STYLES: Record<UiCalloutVariant, CalloutStyle> = {
  info: {
    icon: 'i-lucide-info',
    accent: 'var(--app-blue)',
    bg: 'var(--app-blue-soft)',
    border: 'color-mix(in srgb, var(--app-blue) 30%, transparent)',
  },
  warning: {
    icon: 'i-lucide-triangle-alert',
    accent: 'var(--app-accent-ink)',
    bg: 'var(--app-accent-soft)',
    border: 'color-mix(in srgb, var(--app-accent) 30%, transparent)',
  },
  success: {
    icon: 'i-lucide-circle-check',
    accent: 'var(--app-green)',
    bg: 'var(--app-green-soft)',
    border: 'color-mix(in srgb, var(--app-green) 30%, transparent)',
  },
  neutral: {
    icon: 'i-lucide-info',
    accent: 'var(--app-ink-soft)',
    bg: 'var(--app-bg)',
    border: 'var(--app-line)',
  },
}

/** Resolved style for the current variant. */
const style: ComputedRef<CalloutStyle> = computed((): CalloutStyle => STYLES[props.variant ?? 'info'])
</script>
