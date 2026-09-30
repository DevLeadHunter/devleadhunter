<template>
  <img
    v-if="src"
    :src="src"
    :alt="alt"
    :title="title || alt"
    :width="width"
    :height="height"
    class="inline-block shrink-0 rounded-sm object-cover align-[-2px]"
    loading="lazy"
    decoding="async"
  />
</template>

<script setup lang="ts">
import type { ComputedRef } from 'vue'
import type { ProspectCountryOption } from '~/utils/prospectCountries'
import { ProspectCountries } from '~/utils/prospectCountries'

type UiCountryFlagProps = {
  /** ISO 3166-1 alpha-2 code (FR hidden by default in compact spots). */
  code?: string | null
  /** When false, France still shows its flag (selectors). */
  hideFrance?: boolean
  width?: number
  height?: number
  title?: string
}

const props: UiCountryFlagProps = withDefaults(defineProps<UiCountryFlagProps>(), {
  code: 'FR',
  hideFrance: true,
  width: 20,
  height: 15,
})

const option: ComputedRef<ProspectCountryOption> = computed(
  (): ProspectCountryOption => ProspectCountries.option(props.code),
)

const src: ComputedRef<string | null> = computed((): string | null => {
  if (props.hideFrance && option.value.code === 'FR') return null
  return ProspectCountries.flagSrc(option.value.code)
})

const alt: ComputedRef<string> = computed((): string => option.value.label)
</script>
