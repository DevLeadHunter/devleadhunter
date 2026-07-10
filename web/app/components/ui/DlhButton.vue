<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="[buttonClass, sizeClass, props.class, (disabled || loading) && 'cursor-not-allowed opacity-50']"
  >
    <UIcon v-if="loading" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" aria-hidden="true" />
    <slot />
  </button>
</template>

<script setup lang="ts">
import type { ComputedRef, PropType } from 'vue'
import type { DlhButtonProps, DlhButtonSize, DlhButtonType, DlhButtonVariant } from '~/types/DlhButton'
import { computed } from 'vue'

/**
 * Defines the component props.
 */
const props: DlhButtonProps = defineProps({
  variant: {
    type: String as PropType<DlhButtonVariant>,
    default: 'primary',
  },
  size: {
    type: String as PropType<DlhButtonSize>,
    default: 'lg',
  },
  type: {
    type: String as PropType<DlhButtonType>,
    default: 'button',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  class: {
    type: String,
    default: '',
  },
})

/** Variant class of the button. */
const buttonClass: ComputedRef<string> = computed((): string => {
  const map: Record<DlhButtonVariant, string> = {
    primary: 'app-btn-primary',
    secondary: 'app-btn-secondary',
    danger: 'app-btn-danger',
  }
  return map[props.variant ?? 'primary']
})

/** Size adjustment class of the button. */
const sizeClass: ComputedRef<string> = computed((): string => {
  return (props.size ?? 'lg') === 'md' ? 'h-9 min-h-9 px-4' : ''
})
</script>
