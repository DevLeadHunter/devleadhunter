<template>
  <div
    role="group"
    :aria-label="props.label"
    class="inline-flex gap-0.5 rounded-full border border-[var(--app-line)] bg-[var(--app-surface)] p-0.5"
  >
    <button
      v-for="option in props.options"
      :key="option.value"
      type="button"
      :aria-pressed="option.value === modelValue"
      class="h-7 cursor-pointer rounded-full px-3 text-xs font-medium whitespace-nowrap transition-colors"
      :class="
        option.value === modelValue
          ? 'bg-[var(--app-btn-bg)] text-[var(--app-btn-text)]'
          : 'text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]'
      "
      @click="modelValue = option.value"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<script lang="ts" setup generic="TValue extends SelectFieldValue">
import type { ModelRef, PropType } from 'vue'
import type { SelectFieldOption, SelectFieldValue } from '~/types/SelectField'
import type { UiSegmentedControlProps } from '~/types/UiSegmentedControl'

const modelValue: ModelRef<TValue> = defineModel<TValue>({ required: true })

const props: UiSegmentedControlProps<TValue> = defineProps({
  options: {
    type: Array as PropType<SelectFieldOption<TValue>[]>,
    required: true,
  },
  label: {
    type: String,
    required: true,
  },
})
</script>
