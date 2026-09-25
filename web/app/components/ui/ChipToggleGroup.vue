<template>
  <div class="flex flex-wrap gap-1.5" role="group" :aria-label="props.label">
    <button
      v-for="option in props.options"
      :key="option.value"
      type="button"
      class="cursor-pointer rounded-full border px-2.5 py-1 text-xs transition-colors"
      :class="[
        modelValue.includes(option.value)
          ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-bg)]'
          : 'border-[var(--app-line)] text-[var(--app-ink-soft)] hover:border-[var(--app-ink-soft)]',
        { 'disabled:cursor-not-allowed disabled:opacity-50': props.disabled },
      ]"
      :aria-pressed="modelValue.includes(option.value)"
      :disabled="props.disabled"
      @click="toggleOption(option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<script lang="ts" setup generic="TValue extends SelectFieldValue">
import type { ModelRef, PropType } from 'vue'
import type { SelectFieldOption, SelectFieldValue } from '~/types/SelectField'
import type { UiChipToggleGroupProps } from '~/types/UiChipToggleGroup'

const modelValue: ModelRef<TValue[]> = defineModel<TValue[]>({ required: true })

/** Row of rounded chips, each one adding its value to the bound list or taking it out. */
const props: UiChipToggleGroupProps<TValue> = defineProps({
  options: {
    type: Array as PropType<SelectFieldOption<TValue>[]>,
    required: true,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  label: {
    type: String,
    default: undefined,
  },
})

/**
 * Add a value to the selection, at its end, or take it out when it is already selected.
 * @param value - The value of the clicked chip.
 */
function toggleOption(value: TValue): void {
  modelValue.value = modelValue.value.includes(value)
    ? modelValue.value.filter((item: TValue): boolean => item !== value)
    : [...modelValue.value, value]
}
</script>
