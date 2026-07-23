<template>
  <div role="tablist" class="grid gap-2" :style="gridStyle">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      type="button"
      role="tab"
      :aria-selected="tab.key === modelValue"
      :class="tabClass(tab.key === modelValue)"
      @click="emit('update:modelValue', tab.key)"
    >
      <span class="flex h-6 w-6 shrink-0 items-center justify-center">
        <slot name="icon" :tab="tab" :active="tab.key === modelValue">
          <UIcon v-if="tab.icon" :name="tab.icon" class="h-5 w-5" />
        </slot>
      </span>
      <span class="flex min-w-0 flex-col items-start text-left">
        <span class="text-sm leading-tight font-semibold break-words">{{ tab.label }}</span>
        <span
          v-if="tab.hint"
          class="max-w-full truncate text-xs leading-tight"
          :class="tab.key === modelValue ? 'text-[var(--app-surface)]/75' : 'text-[var(--app-ink-soft)]'"
        >
          {{ tab.hint }}
        </span>
      </span>
    </button>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import { computed } from 'vue'
import type { UiTab, UiTabsProps } from '~/types/UiTabs'

/** Segmented tabs; custom per-tab icon via scoped slot. */
const props: UiTabsProps = defineProps({
  tabs: {
    type: Array as PropType<UiTab[]>,
    required: true,
  },
  modelValue: {
    type: String,
    required: true,
  },
})

const emit: {
  (e: 'update:modelValue', key: string): void
} = defineEmits<{
  (e: 'update:modelValue', key: string): void
}>()

/** Equal-width columns, one per tab. */
const gridStyle: ComputedRef<Record<string, string>> = computed(
  (): Record<string, string> => ({
    gridTemplateColumns: `repeat(${props.tabs.length}, minmax(0, 1fr))`,
  }),
)

/**
 * Resolve the classes of a tab button for a given selected state.
 * @param active - Whether this tab is the selected one.
 * @returns The Tailwind class string for the button.
 */
function tabClass(active: boolean): string {
  const base: string =
    'flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--app-ink-soft)]'
  return active
    ? `${base} border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-surface)]`
    : `${base} border-[var(--app-line)] bg-[var(--app-surface)] text-[var(--app-ink-soft)] hover:border-[var(--app-ink-soft)] hover:text-[var(--app-ink)]`
}
</script>
