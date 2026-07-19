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

    <!-- Smooth height reveal via animatable grid rows (0fr → 1fr), no layout jump -->
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

<script setup lang="ts">
import type { Ref } from 'vue'
import { ref } from 'vue'

/**
 * A settings « card » that expands/collapses its content smoothly. Shares the
 * app's card chrome (solid surface, icon + bold title) and animates height with
 * an interpolatable grid instead of the native <details> snap.
 */
const props = defineProps({
  /** Lucide icon name shown before the title (e.g. ``i-lucide-scissors``). */
  icon: { type: String, required: true },
  /** Card title. */
  title: { type: String, required: true },
  /** Optional muted suffix shown after the title (e.g. ``facultatif``). */
  suffix: { type: String, default: '' },
  /** Whether the card starts expanded. */
  defaultOpen: { type: Boolean, default: false },
})

const isOpen: Ref<boolean> = ref<boolean>(props.defaultOpen)
</script>
