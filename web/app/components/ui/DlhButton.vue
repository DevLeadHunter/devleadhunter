<template>
  <UButton
    :color="nuxtColor"
    :variant="nuxtVariant"
    :size="size"
    :type="type"
    :disabled="disabled"
    :loading="loading"
    :class="props.class"
  >
    <slot />
  </UButton>
</template>

<script setup lang="ts">
type DlhButtonVariant = 'primary' | 'secondary' | 'danger'
type DlhButtonSize = 'md' | 'lg'

const props = withDefaults(
  defineProps<{
    variant?: DlhButtonVariant
    size?: DlhButtonSize
    type?: 'button' | 'submit' | 'reset'
    disabled?: boolean
    loading?: boolean
    class?: string
  }>(),
  {
    variant: 'primary',
    size: 'lg',
    type: 'button',
    disabled: false,
    loading: false,
    class: '',
  },
)

const nuxtColor = computed((): 'primary' | 'neutral' | 'error' => {
  if (props.variant === 'secondary') {
    return 'neutral'
  }
  if (props.variant === 'danger') {
    return 'error'
  }
  return 'primary'
})

const nuxtVariant = computed((): 'solid' | 'outline' => {
  return props.variant === 'secondary' ? 'outline' : 'solid'
})
</script>
