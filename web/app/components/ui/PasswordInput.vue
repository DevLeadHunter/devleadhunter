<template>
  <div class="relative w-full">
    <input
      :id="id"
      :value="modelValue"
      :type="showPassword ? 'text' : 'password'"
      :required="required"
      :placeholder="placeholder"
      :class="inputClasses"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
    <button
      type="button"
      :class="['absolute top-1/2 right-3 -translate-y-1/2 cursor-pointer transition-colors', toggleClasses]"
      :aria-label="showPassword ? 'Hide password' : 'Show password'"
      @click="showPassword = !showPassword"
    >
      <svg
        v-if="showPassword"
        class="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        aria-hidden="true"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88"
        />
      </svg>
      <svg
        v-else
        class="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        aria-hidden="true"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"
        />
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    </button>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import { computed, ref } from 'vue'
import type { UiPasswordInputAppearance, UiPasswordInputProps } from '~/types/UiPasswordInput'

/** Password field with show/hide toggle; `app` or `landing` appearance. */
const props: UiPasswordInputProps = defineProps({
  id: {
    type: String,
    required: true,
  },
  modelValue: {
    type: String,
    required: true,
  },
  placeholder: {
    type: String,
    default: '',
  },
  required: {
    type: Boolean,
    default: false,
  },
  hasError: {
    type: Boolean,
    default: false,
  },
  appearance: {
    type: String as PropType<UiPasswordInputAppearance>,
    default: 'app',
  },
})

defineEmits<{
  'update:modelValue': [value: string]
}>()

const showPassword: Ref<boolean> = ref(false)

/**
 * Input classes resolved from the appearance + error state.
 */
const inputClasses: ComputedRef<string[]> = computed((): string[] => {
  if (props.appearance === 'landing') {
    return ['landing-input pr-10', props.hasError ? 'landing-input--error' : '']
  }
  return ['input-field pr-10', props.hasError ? 'border-[var(--app-red)]' : '']
})

/**
 * Show/hide toggle button classes resolved from the appearance.
 */
const toggleClasses: ComputedRef<string> = computed((): string =>
  props.appearance === 'landing'
    ? 'text-[#6b6355] hover:text-[#1b1813]'
    : 'text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]',
)
</script>
