<template>
  <Teleport to="body">
    <div
      v-if="open && items.length"
      class="fixed z-[60] max-h-64 w-64 overflow-y-auto rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] py-1 shadow-2xl"
      :style="{ top: `${position.top}px`, left: `${position.left}px` }"
    >
      <button
        v-for="(variable, index) in items"
        :key="variable.key"
        type="button"
        class="flex w-full items-start gap-2 px-3 py-1.5 text-left transition-colors"
        :class="index === activeIndex ? 'bg-[var(--app-surface-2)]' : 'hover:bg-[var(--app-surface-2)]/60'"
        @mousedown.prevent="emit('select', variable)"
        @mouseenter="emit('activate', index)"
      >
        <span class="font-mono text-[11px] text-[var(--app-accent-ink)]">{{ variable.token }}</span>
        <span class="text-muted min-w-0 flex-1 truncate text-[11px]">{{ variable.label }}</span>
      </button>
    </div>
  </Teleport>
</template>

<script lang="ts" setup>
import type { UiVariableAutocompleteEmits } from '~/types/UiVariableAutocomplete'
import type { EmitFn, PropType } from 'vue'
import type { EmailVariable } from '~/utils/emailVariables'
import type { AutocompletePosition } from '~/composables/useVariableInsertion'

/** Inline autocomplete for template variable insertion. */
defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  items: {
    type: Array as PropType<EmailVariable[]>,
    required: true,
  },
  activeIndex: {
    type: Number,
    required: true,
  },
  position: {
    type: Object as PropType<AutocompletePosition>,
    required: true,
  },
})

const emit: EmitFn<UiVariableAutocompleteEmits> = defineEmits<UiVariableAutocompleteEmits>()
</script>
