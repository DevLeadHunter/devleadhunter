<template>
  <USelectMenu
    v-model="modelValue"
    :items="props.options"
    value-key="value"
    label-key="label"
    class="w-full"
    placeholder="Sélectionner…"
  />
</template>

<script lang="ts" setup>
import type { ModelRef, PropType } from 'vue'
import type { SelectFieldOption, SelectFieldProps } from '~/types/SelectField'

const modelValue: Ref<string, string> & [ModelRef<string, string, string, string>, Record<string, true | undefined>] =
  defineModel<string>({ required: true })

/** Native select whose entries come from a typed option list. */
const props: SelectFieldProps = defineProps({
  options: {
    type: Array as PropType<SelectFieldOption[]>,
    required: true,
  },
})
</script>
