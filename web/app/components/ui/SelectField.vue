<template>
  <USelectMenu
    v-model="modelValue"
    :items="options"
    value-key="value"
    label-key="label"
    class="w-full"
    placeholder="Sélectionner…"
  />
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { SelectFieldOption } from '~/types/SelectField'

const modelValue = defineModel<string>({ required: true })

defineProps({
  options: {
    type: Array as PropType<SelectFieldOption[]>,
    required: true,
  },
})
</script>
