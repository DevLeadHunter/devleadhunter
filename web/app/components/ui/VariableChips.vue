<template>
  <div class="flex flex-wrap gap-1.5">
    <div v-for="variable in variables" :key="variable.key" class="group relative">
      <button
        type="button"
        class="rounded-md border border-[var(--app-line)] bg-[var(--app-surface)] px-2 py-1 font-mono text-[11px] text-[var(--app-ink-soft)] transition-colors hover:border-[var(--app-ink-soft)] hover:text-[var(--app-ink)]"
        @mouseenter="updateAlign(variable.key, $event)"
        @focusin="updateAlign(variable.key, $event)"
        @click="emit('insert', variable.token)"
      >
        {{ variable.token }}
      </button>

      <div
        class="pointer-events-none absolute bottom-full z-10 mb-1.5 hidden w-max max-w-[260px] rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-2.5 text-left shadow-xl group-focus-within:block group-hover:block"
        :class="alignByKey[variable.key] === 'right' ? 'right-0' : 'left-0'"
      >
        <p class="text-xs font-semibold text-[var(--app-ink)]">{{ variable.label }}</p>
        <p class="text-muted mt-0.5 text-[11px] leading-snug">{{ variable.description }}</p>
        <p class="mt-1.5 text-[11px] text-[var(--app-ink-soft)]">
          <span class="text-[var(--app-faint)]">Ex :</span> {{ variable.example }}
        </p>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { UiVariableChipsEmits } from '~/types/UiVariableChips'
import type { EmitFn, Ref } from 'vue'
import type { EmailVariable } from '~/utils/emailVariables'
import { ref } from 'vue'
import { EmailVariables } from '~/utils/emailVariables'

const emit: EmitFn<UiVariableChipsEmits> = defineEmits<UiVariableChipsEmits>()

/** The available variables rendered as chips. */
const variables: EmailVariable[] = EmailVariables.catalog

/** Approximate tooltip width (matches `max-w-[260px]`) used to decide the flip. */
const TOOLTIP_WIDTH: number = 264

/** Per-chip tooltip alignment (`right` when it would overflow the viewport). */
const alignByKey: Ref<Record<string, 'left' | 'right'>> = ref({})

/**
 * Decide whether a chip's tooltip should open left (default) or flip to the
 * right edge, based on the space available to the right of the chip.
 * @param key - The chip's variable key.
 * @param event - The triggering mouse/focus event (its target is the chip).
 */
function updateAlign(key: string, event: Event): void {
  const target: EventTarget | null = event.currentTarget
  if (!(target instanceof HTMLElement)) return
  const rect: DOMRect = target.getBoundingClientRect()
  const overflowsRight: boolean = rect.left + TOOLTIP_WIDTH > window.innerWidth - 12
  alignByKey.value = { ...alignByKey.value, [key]: overflowsRight ? 'right' : 'left' }
}
</script>
