<template>
  <USwitch
    :id="props.id"
    :model-value="props.modelValue"
    :label="props.label"
    :disabled="props.disabled"
    color="neutral"
    size="md"
    @update:model-value="$emit('update:modelValue', $event)"
  />
</template>

<script lang="ts" setup>
import type { UiSwitchProps } from '~/types/UiSwitch'

/** Binary toggle mirroring the native checkbox semantics. */
const props: UiSwitchProps = defineProps({
  id: {
    type: String,
    default: undefined,
  },
  modelValue: {
    type: Boolean,
    required: true,
  },
  label: {
    type: String,
    default: undefined,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

defineEmits<{
  'update:modelValue': [value: boolean]
}>()
</script>
