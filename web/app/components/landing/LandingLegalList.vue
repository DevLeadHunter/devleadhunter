<template>
  <ul class="grid list-disc gap-2 pl-5 marker:text-[#e8a33c]">
    <li v-for="itemKey in props.itemKeys" :key="itemKey">
      <template v-if="props.isTermAfterText">
        {{ $t(`${props.baseKey}.${itemKey}.text`) }}
        <strong class="font-semibold text-[#1b1813]">{{ $t(`${props.baseKey}.${itemKey}.term`) }}</strong>
      </template>
      <template v-else>
        <strong class="font-semibold text-[#1b1813]">{{ $t(`${props.baseKey}.${itemKey}.term`) }}</strong>
        {{ $t(`${props.baseKey}.${itemKey}.text`) }}
      </template>
    </li>
  </ul>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { LandingLegalListProps } from '~/types/LandingLegalList'

/** Each item key needs a `term` and a `text` message under `baseKey`. */
const props: LandingLegalListProps = defineProps({
  baseKey: {
    type: String,
    required: true,
  },
  itemKeys: {
    type: Array as PropType<string[]>,
    required: true,
  },
  isTermAfterText: {
    type: Boolean,
    default: false,
  },
})
</script>
