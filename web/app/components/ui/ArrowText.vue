<template>
  <span
    ><template v-for="(part, index) in parts" :key="index"
      ><UIcon v-if="index > 0" name="i-lucide-arrow-right" class="inline-block h-[1em] w-[1em] align-[-0.125em]" />{{
        part
      }}</template
    ></span
  >
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import { computed } from 'vue'
import type { UiArrowTextProps } from '~/types/UiArrowText'

/** Text rendered as is, except that each « → » becomes the arrow icon (spaces around it are kept). */
const props: UiArrowTextProps = defineProps({
  text: {
    type: String,
    required: true,
  },
})

const parts: ComputedRef<string[]> = computed((): string[] => props.text.split('→'))
</script>
