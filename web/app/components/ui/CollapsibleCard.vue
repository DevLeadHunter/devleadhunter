<template>
  <div class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)]">
    <button
      type="button"
      class="flex w-full cursor-pointer items-center justify-between gap-3 px-4 py-3.5 text-left select-none"
      :aria-expanded="isOpen"
      @click="isOpen = !isOpen"
    >
      <span class="flex items-center gap-3 text-sm font-semibold text-[var(--app-ink)]">
        <UIcon :name="icon" class="h-4 w-4 shrink-0" />
        {{ title }}
        <span v-if="suffix" class="text-muted text-xs font-normal">{{ suffix }}</span>
      </span>
      <UIcon
        name="i-lucide-chevron-down"
        class="text-muted h-4 w-4 shrink-0 transition-transform duration-300 ease-out"
        :class="{ 'rotate-180': isOpen }"
      />
    </button>

    <div
      class="grid transition-[grid-template-rows] duration-300 ease-out motion-reduce:transition-none"
      :class="isOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'"
    >
      <div class="overflow-hidden">
        <div class="border-t border-[var(--app-line)]">
          <slot />
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import type { UiCollapsibleCardProps } from '~/types/UiCollapsibleCard'
import { ref } from 'vue'

/** Expandable settings card with smooth height animation. */
const props: UiCollapsibleCardProps = defineProps({
  icon: { type: String, required: true },
  title: { type: String, required: true },
  suffix: { type: String, default: '' },
  defaultOpen: { type: Boolean, default: false },
})

const isOpen: Ref<boolean> = ref(props.defaultOpen ?? false)
</script>
