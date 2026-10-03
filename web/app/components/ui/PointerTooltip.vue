<template>
  <Teleport to="body">
    <div
      v-if="props.isOpen"
      role="tooltip"
      class="pointer-events-none fixed z-[120] w-max max-w-[280px] rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-3 py-2 text-xs leading-relaxed text-[var(--app-ink-soft)] shadow-[var(--app-shadow-lift)]"
      :style="position"
    >
      <slot />
    </div>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import { computed } from 'vue'
import type { UiPointerTooltipProps } from '~/types/UiPointerTooltip'

const props: UiPointerTooltipProps = defineProps({
  isOpen: {
    type: Boolean,
    required: true,
  },
  pointerX: {
    type: Number,
    required: true,
  },
  pointerY: {
    type: Number,
    required: true,
  },
})

const HALF_WIDEST_TOOLTIP: number = 148
const TOP_ROOM: number = 120

const position: ComputedRef<Record<string, string>> = computed((): Record<string, string> => {
  const viewportWidth: number = document.documentElement.clientWidth
  const left: number = Math.min(Math.max(props.pointerX, HALF_WIDEST_TOOLTIP), viewportWidth - HALF_WIDEST_TOOLTIP)
  const isBelow: boolean = props.pointerY < TOP_ROOM
  return {
    left: `${left}px`,
    top: `${isBelow ? props.pointerY + 18 : props.pointerY - 12}px`,
    transform: isBelow ? 'translateX(-50%)' : 'translate(-50%, -100%)',
  }
})
</script>
