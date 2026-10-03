<template>
  <span
    v-if="show"
    class="ui-country-flag inline-flex shrink-0 items-center justify-center overflow-hidden rounded-[3px] ring-1 ring-[var(--app-line)]/80"
    :class="sizeClass"
    :title="props.title || label"
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
    <svg v-else-if="countryCode === 'CA'" viewBox="0 0 40 20" class="h-full w-full" aria-hidden="true">
      <rect width="40" height="20" fill="#fff" />
      <rect width="10" height="20" fill="#D80621" />
      <rect x="30" width="10" height="20" fill="#D80621" />
      <path
        fill="#D80621"
        d="M20 3.5l1.3 2.6 2-1-.7 3.4 1.6-.6.4 1.4 2.2-1.1-.6 2.2 1.3.6-3.6 3 .4 1.2-3.6-.5.2 2.8h-1.8l.2-2.8-3.6.5.4-1.2-3.6-3 1.3-.6-.6-2.2 2.2 1.1.4-1.4 1.6.6-.7-3.4 2 1z"
      />
    </svg>
    <svg v-else-if="countryCode === 'FR'" viewBox="0 0 30 20" class="h-full w-full" aria-hidden="true">
      <rect width="10" height="20" fill="#002395" />
      <rect x="10" width="10" height="20" fill="#fff" />
      <rect x="20" width="10" height="20" fill="#ED2939" />
    </svg>
  </span>
</template>

<script lang="ts" setup>
import type { UiCountryFlagProps, UiCountryFlagSize } from '~/types/UiCountryFlag'
import type { ComputedRef, PropType } from 'vue'
import { computed } from 'vue'
import { ProspectCountries } from '~/utils/prospectCountries'

/** Inline SVG flag of a prospect's country, hidden for France by default so French rows stay unchanged. */
const props: UiCountryFlagProps = defineProps({
  code: {
    type: String as PropType<string | null>,
    default: 'FR',
  },
  hideFrance: {
    type: Boolean,
    default: true,
  },
  size: {
    type: String as PropType<UiCountryFlagSize>,
    default: 'compact',
  },
  title: {
    type: String,
    default: undefined,
  },
})

const countryCode: ComputedRef<string> = computed((): string => ProspectCountries.option(props.code).code)

const show: ComputedRef<boolean> = computed((): boolean => !(props.hideFrance && countryCode.value === 'FR'))

const label: ComputedRef<string> = computed((): string => ProspectCountries.option(props.code).label)

const sizeClass: ComputedRef<string> = computed((): string =>
  props.size === 'default' ? 'h-[13px] w-[18px]' : 'h-[11px] w-[15px]',
)
</script>
