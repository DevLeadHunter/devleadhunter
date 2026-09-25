<template>
  <!-- Borderless: the parent row owns the separator, so the active underline sits on it. -->
  <div role="tablist" class="no-scrollbar flex max-w-full items-center gap-1 overflow-x-auto">
    <button
      v-for="tab in props.tabs"
      :key="tab.key"
      type="button"
      role="tab"
      :aria-selected="tab.key === props.modelValue"
      :class="tabClass(tab.key === props.modelValue)"
      @click="emit('update:modelValue', tab.key)"
    >
      {{ tab.label }}
      <span
        v-if="tab.count !== undefined"
        class="font-label ml-1.5 rounded-full bg-[var(--app-surface-2)] px-2 py-0.5 text-xs"
      >
        {{ tab.count }}
      </span>
      <span
        v-if="tab.key === props.modelValue"
        class="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-[var(--app-accent)]"
      ></span>
    </button>
  </div>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { UiFilterTab, UiFilterTabsProps } from '~/types/UiFilterTabs'

/**
 * Compact underlined tabs that slice the list below them. Deliberately lighter
 * than the segmented `UiTabs`, which is meant for choices that deserve their own
 * card and would eat the top of a list page.
 */
const props: UiFilterTabsProps = defineProps({
  tabs: {
    type: Array as PropType<UiFilterTab[]>,
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

/**
 * Resolve the classes of a tab button for a given selected state.
 * @param active - Whether this tab is the selected one.
 * @returns The Tailwind class string for the button.
 */
function tabClass(active: boolean): string {
  const base: string =
    'relative shrink-0 cursor-pointer px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--app-ink-soft)] rounded-t'
  return active ? `${base} text-[var(--app-ink)]` : `${base} text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]`
}
</script>
