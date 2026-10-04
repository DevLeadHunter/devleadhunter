<template>
  <!-- Borderless: the parent row owns the separator, so the active underline sits on it. -->
  <div
    ref="tabListElement"
    role="tablist"
    class="no-scrollbar -mb-px flex max-w-full touch-pan-x items-center gap-1 overflow-x-auto overflow-y-hidden overscroll-x-contain"
  >
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
        class="absolute inset-x-3 bottom-0 h-0.5 rounded-full bg-[var(--app-accent)]"
      ></span>
    </button>
  </div>
</template>

<script lang="ts" setup>
import type { PropType, Ref } from 'vue'
import type { UiFilterTab, UiFilterTabsProps } from '~/types/UiFilterTabs'
import { nextTick, ref, watch } from 'vue'

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

const tabListElement: Ref<HTMLElement | null> = ref(null)

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

/**
 * Slide the row so the selected tab is fully visible, without moving the page.
 * @returns A promise resolved once the row is in place.
 */
async function revealSelectedTab(): Promise<void> {
  await nextTick()
  const tabList: HTMLElement | null = tabListElement.value
  const selectedTab: HTMLElement | null = tabList?.querySelector<HTMLElement>('[aria-selected="true"]') ?? null
  if (tabList === null || selectedTab === null) return
  const rowBox: DOMRect = tabList.getBoundingClientRect()
  const tabBox: DOMRect = selectedTab.getBoundingClientRect()
  if (tabBox.left < rowBox.left) {
    tabList.scrollBy({ left: tabBox.left - rowBox.left, behavior: 'smooth' })
  } else if (tabBox.right > rowBox.right) {
    tabList.scrollBy({ left: tabBox.right - rowBox.right, behavior: 'smooth' })
  }
}

watch(
  (): string => props.modelValue,
  (): void => {
    revealSelectedTab()
  },
)
</script>
