<template>
  <div
    role="group"
    :aria-label="props.label"
    class="gap-0.5 rounded-full border border-[var(--app-line)] bg-[var(--app-surface)] p-0.5"
    :class="props.isStretchedOnNarrowScreens ? 'flex w-full @3xl:inline-flex @3xl:w-auto' : 'inline-flex'"
  >
    <button
      v-for="option in props.options"
      :key="option.value"
      type="button"
      :aria-pressed="option.value === modelValue"
      class="cursor-pointer rounded-full font-medium whitespace-nowrap transition-colors"
      :class="[
        props.isStretchedOnNarrowScreens
          ? 'h-10 flex-1 px-3.5 text-sm @3xl:h-7 @3xl:flex-none @3xl:px-3 @3xl:text-xs'
          : 'h-7 px-3 text-xs',
        option.value === modelValue
          ? 'bg-[var(--app-btn-bg)] text-[var(--app-btn-text)]'
          : 'text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]',
      ]"
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

/** Pill switch between a few options; on narrow screens it can span the width with finger-sized options. */
const props: UiSegmentedControlProps<TValue> = defineProps({
  options: {
    type: Array as PropType<SelectFieldOption<TValue>[]>,
    required: true,
  },
  label: {
    type: String,
    required: true,
  },
  isStretchedOnNarrowScreens: {
    type: Boolean,
    default: false,
  },
})
</script>
