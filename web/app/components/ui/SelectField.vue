<template>
  <!-- Portalled to body with no z-index of its own: without this it opens behind a drawer. On a touch screen the
       trigger keeps the 44px finger target of the app's other fields. -->
  <USelectMenu
    v-model="selectedOption"
    :items="props.options"
    label-key="label"
    :placeholder="props.placeholder"
    :disabled="props.disabled"
    :ui="{ base: 'pointer-coarse:min-h-11', content: 'z-[110]' }"
    class="w-full"
  />
</template>

<script lang="ts" setup generic="TValue extends SelectFieldValue">
import type { ModelRef, PropType, WritableComputedRef } from 'vue'
import { computed } from 'vue'
import type { SelectFieldOption, SelectFieldProps, SelectFieldValue } from '~/types/SelectField'

const modelValue: ModelRef<TValue> = defineModel<TValue>({ required: true })

/** Searchable select whose entries come from a typed option list. */
const props: SelectFieldProps<TValue> = defineProps({
  options: {
    type: Array as PropType<SelectFieldOption<TValue>[]>,
    required: true,
  },
  placeholder: {
    type: String,
    default: 'Sélectionner…',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

// Driven by the option object: `value-key` cannot resolve a key through a generic.
const selectedOption: WritableComputedRef<SelectFieldOption<TValue> | undefined> = computed({
  get: (): SelectFieldOption<TValue> | undefined =>
    props.options.find((option: SelectFieldOption<TValue>): boolean => option.value === modelValue.value),
  set: (option: SelectFieldOption<TValue> | undefined): void => {
    if (option) modelValue.value = option.value
  },
})
</script>
