<template>
  <span
    v-if="show"
    class="ui-country-flag inline-flex shrink-0 items-center justify-center overflow-hidden rounded-[3px] ring-1 ring-[var(--app-line)]/80"
    :class="sizeClass"
    :title="title || label"
    role="img"
    :aria-label="label"
  >
    <!-- Inline SVG — lisible sur Windows, taille maîtrisée (pas de PNG flagcdn). -->
    <svg v-if="countryCode === 'CH'" viewBox="0 0 32 32" class="h-full w-full" aria-hidden="true">
      <rect width="32" height="32" fill="#D52B1E" />
      <rect x="14" y="6" width="4" height="20" fill="#fff" />
      <rect x="6" y="14" width="20" height="4" fill="#fff" />
    </svg>
    <svg v-else-if="countryCode === 'BE'" viewBox="0 0 30 20" class="h-full w-full" aria-hidden="true">
      <rect width="10" height="20" fill="#000" />
      <rect x="10" width="10" height="20" fill="#FDDA24" />
      <rect x="20" width="10" height="20" fill="#EF3340" />
    </svg>
    <svg v-else-if="countryCode === 'LU'" viewBox="0 0 30 20" class="h-full w-full" aria-hidden="true">
      <rect width="30" height="6.67" fill="#EF3340" />
      <rect y="6.67" width="30" height="6.67" fill="#fff" />
      <rect y="13.33" width="30" height="6.67" fill="#00A1DE" />
    </svg>
    <svg v-else-if="countryCode === 'FR'" viewBox="0 0 30 20" class="h-full w-full" aria-hidden="true">
      <rect width="10" height="20" fill="#002395" />
      <rect x="10" width="10" height="20" fill="#fff" />
      <rect x="20" width="10" height="20" fill="#ED2939" />
    </svg>
  </span>
</template>

<script setup lang="ts">
import type { ComputedRef } from 'vue'
import { ProspectCountries } from '~/utils/prospectCountries'

type UiCountryFlagProps = {
  code?: string | null
  hideFrance?: boolean
  /** compact = liste prospects ; default = fiche prospect */
  size?: 'compact' | 'default'
  title?: string
}

const props: UiCountryFlagProps = withDefaults(defineProps<UiCountryFlagProps>(), {
  code: 'FR',
  hideFrance: true,
  size: 'compact',
})

const normalized: ComputedRef<string> = computed((): string => ProspectCountries.option(props.code).code)

const show: ComputedRef<boolean> = computed((): boolean => !(props.hideFrance && normalized.value === 'FR'))

const label: ComputedRef<string> = computed((): string => ProspectCountries.option(props.code).label)

const sizeClass: ComputedRef<string> = computed((): string =>
  props.size === 'default' ? 'h-[13px] w-[18px]' : 'h-[11px] w-[15px]',
)

const countryCode: ComputedRef<string> = normalized
</script>
