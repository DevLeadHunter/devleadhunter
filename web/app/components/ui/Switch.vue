<template>
  <USwitch
    :id="id"
    :model-value="modelValue"
    :label="label"
    :disabled="disabled"
    color="neutral"
    size="md"
    @update:model-value="$emit('update:modelValue', $event)"
  />
</template>

<script setup lang="ts">
defineProps<{
  id?: string
  modelValue: boolean
  label?: string
  disabled?: boolean
}>()

defineEmits<{
  'update:modelValue': [value: boolean]
}>()
</script>
