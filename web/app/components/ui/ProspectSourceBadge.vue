<template>
  <span
    :class="[
      'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold',
      config.bg,
      config.text,
    ]"
  >
    <img
      v-if="config.logoUrl"
      :src="config.logoUrl"
      :alt="config.label"
      class="h-3.5 w-3.5 shrink-0 object-contain"
      loading="lazy"
    />

    <UIcon v-else :name="config.icon" class="h-3.5 w-3.5 shrink-0" />

    {{ config.label }}
  </span>
</template>

<script lang="ts" setup>
import type { ProspectSourcePresentation, UiProspectSourceBadgeProps } from '~/types/UiProspectSourceBadge'
import type { ComputedRef, PropType } from 'vue'
import { computed } from 'vue'
import type { ProspectSource } from '~/types'

/** Badge naming the acquisition source a prospect came from. */
const props: UiProspectSourceBadgeProps = defineProps({
  source: {
    type: String as PropType<ProspectSource | string>,
    required: true,
  },
})

/** Per-source badge colours and favicon logos for prospect origin. */
const SOURCE_CONFIG: Record<string, ProspectSourcePresentation> = {
  pagesjaunes: {
    label: 'Pages Jaunes',
    logoUrl: 'https://www.google.com/s2/favicons?domain=pagesjaunes.fr&sz=32',
    icon: 'i-lucide-book-open',
    bg: 'bg-[#F7C500]',
    text: 'text-[#1a1200]',
  },
  google: {
    label: 'Google',
    logoUrl: 'https://www.google.com/s2/favicons?domain=google.com&sz=32',
    icon: 'i-lucide-globe',
    bg: 'bg-[#4285F4]',
    text: 'text-white',
  },
  osm: {
    // OSM/Bright Data : leur favicon distant est illisible à 14 px, d'où une icône locale.
    label: 'OpenStreetMap',
    logoUrl: null,
    icon: 'i-lucide-map-pinned',
    bg: 'bg-[#3F7E1E]',
    text: 'text-white',
  },
  yelp: {
    label: 'Yelp',
    logoUrl: 'https://www.google.com/s2/favicons?domain=yelp.com&sz=32',
    icon: 'i-lucide-star',
    bg: 'bg-[#D32323]',
    text: 'text-white',
  },
  brightdata: {
    label: 'Bright Data',
    logoUrl: null,
    icon: 'i-lucide-radar',
    bg: 'bg-[#12395F]',
    text: 'text-[#9BD3FF]',
  },
  auto: {
    label: 'Auto',
    logoUrl: null,
    icon: 'i-lucide-wand-sparkles',
    bg: 'bg-[#7C3AED]',
    text: 'text-white',
  },
  manual: {
    label: 'Manuel',
    logoUrl: null,
    icon: 'i-lucide-pen-line',
    bg: 'bg-[#57534E]',
    text: 'text-white',
  },
}

/** Fallback for unknown / future sources */
const FALLBACK: ProspectSourcePresentation = {
  label: '',
  logoUrl: null,
  icon: 'i-lucide-database',
  bg: 'bg-[#4B5563]',
  text: 'text-white',
}

const config: ComputedRef<ProspectSourcePresentation> = computed((): ProspectSourcePresentation => {
  return SOURCE_CONFIG[props.source] ?? { ...FALLBACK, label: props.source }
})
</script>
