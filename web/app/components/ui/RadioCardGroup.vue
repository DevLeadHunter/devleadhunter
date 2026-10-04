<template>
  <div class="grid gap-2" role="radiogroup" :aria-labelledby="props.labelledBy">
    <button
      v-for="option in props.options"
      :key="option.value"
      type="button"
      role="radio"
      :aria-checked="modelValue === option.value"
      class="flex w-full cursor-pointer items-start gap-3 rounded-xl border px-3.5 py-3 text-left transition-colors focus-visible:ring-2 focus-visible:ring-[var(--app-ink-soft)] focus-visible:outline-none"
      :class="
        modelValue === option.value
          ? 'border-[var(--app-ink)] bg-[var(--app-surface-2)]'
          : 'border-[var(--app-line)] hover:border-[var(--app-ink-soft)]'
      "
      @click="modelValue = option.value"
    >
      <UIcon :name="option.icon" class="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-ink)]" />
      <span class="min-w-0 flex-1">
        <span class="block text-sm font-medium text-[var(--app-ink)]">{{ option.label }}</span>
        <span class="mt-0.5 block text-xs leading-relaxed text-[var(--app-ink-soft)]">{{ option.description }}</span>
      </span>
      <span
        class="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border"
        :class="
          modelValue === option.value ? 'border-[var(--app-ink)] bg-[var(--app-ink)]' : 'border-[var(--app-faint)]'
        "
      >
        <UIcon v-if="modelValue === option.value" name="i-lucide-check" class="h-3 w-3 text-[var(--app-bg)]" />
      </span>
    </button>
  </div>
</template>

<script lang="ts" setup generic="TValue extends SelectFieldValue">
import type { ModelRef, PropType } from 'vue'
import type { SelectFieldValue } from '~/types/SelectField'
import type { UiRadioCardGroupProps, UiRadioCardOption } from '~/types/UiRadioCardGroup'

const modelValue: ModelRef<TValue> = defineModel<TValue>({ required: true })

/** Single choice among options that each need a sentence: one card per option; the caller sets the grid columns. */
const props: UiRadioCardGroupProps<TValue> = defineProps({
  options: {
    type: Array as PropType<UiRadioCardOption<TValue>[]>,
    required: true,
  },
  labelledBy: {
    type: String,
    required: true,
  },
})
</script>
