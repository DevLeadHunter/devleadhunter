<template>
  <ul class="flex flex-wrap gap-1.5">
    <li
      v-for="label in props.labels"
      :key="label"
      class="inline-flex max-w-full items-center gap-1 rounded-full border border-[var(--app-ink)] bg-[var(--app-ink)] py-1 pr-1.5 pl-2.5 text-xs font-medium text-[var(--app-bg)]"
    >
      <span class="min-w-0 truncate">{{ label }}</span>
      <button
        type="button"
        class="flex h-4 w-4 shrink-0 cursor-pointer items-center justify-center rounded-full transition-colors hover:bg-[var(--app-bg)]/20 disabled:cursor-not-allowed disabled:opacity-50"
        :aria-label="`Retirer ${label}`"
        :disabled="props.disabled"
        @click="emit('remove', label)"
      >
        <UIcon name="i-lucide-x" class="h-3 w-3" />
      </button>
    </li>
  </ul>
</template>

<script lang="ts" setup>
import type { EmitFn, PropType } from 'vue'
import type { UiRemovableChipListEmits, UiRemovableChipListProps } from '~/types/UiRemovableChipList'

/** Values picked in a multi-entry field, each shown as a chip that can be taken out. */
const props: UiRemovableChipListProps = defineProps({
  labels: {
    type: Array as PropType<string[]>,
    required: true,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiRemovableChipListEmits> = defineEmits<UiRemovableChipListEmits>()
</script>
