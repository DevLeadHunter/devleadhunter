<template>
  <span
    :class="[
      'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold',
      config.bg,
      config.text,
    ]"
  >
    <!-- Real brand favicon (pagesjaunes, google, osm, yelp, brightdata) -->
    <img
      v-if="config.logoUrl"
      :src="config.logoUrl"
      :alt="config.label"
      class="h-3.5 w-3.5 shrink-0 object-contain"
      loading="lazy"
    />
    <!-- Fallback icon for sources without a real website (auto, unknown) -->
    <UIcon v-else :name="config.icon" class="h-3.5 w-3.5 shrink-0" />

    {{ config.label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ProspectSource } from '~/types'

// ─── Props ────────────────────────────────────────────────────────────────────

interface Props {
  /** Source value from the backend Source enum */
  source: ProspectSource | string
}

const props = defineProps<Props>()

// ─── Per-source visual config ─────────────────────────────────────────────────

interface SourceConfig {
  /** Display label */
  label: string
  /**
   * Remote favicon URL (Google's favicon service).
   * Null for internal / synthetic sources that have no real website logo.
   */
  logoUrl: string | null
  /** Lucide icon name used when logoUrl is null */
  icon: string
  /** Tailwind solid background class — full brand colour */
  bg: string
  /** Tailwind text class — chosen for contrast against the background */
  text: string
}

/**
 * Visual configuration per source.
 *
 * Background colours are the official brand primaries:
 *   Pages Jaunes  #F7C500  (PJ yellow)
 *   Google        #4285F4  (Google blue)
 *   OpenStreetMap #73B73B  (OSM green)
 *   Yelp          #D32323  (Yelp red)
 *   BrightData    #0099E5  (BrightData cyan-blue)
 *   Auto          #7C3AED  (purple — composite source)
 *
 * Logos are loaded via Google's favicon service so they always match the
 * source's current brand icon without storing local assets.
 */
const SOURCE_CONFIG: Record<string, SourceConfig> = {
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
    // OSM/Bright Data : favicon distant illisible à 14 px (logo détaillé fondu
    // dans le fond) → icône lucide nette + couleur franche, au niveau des
    // badges Pages Jaunes / Yelp.
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
const FALLBACK: SourceConfig = {
  label: '',
  logoUrl: null,
  icon: 'i-lucide-database',
  bg: 'bg-[#4B5563]',
  text: 'text-white',
}

const config = computed((): SourceConfig => {
  return SOURCE_CONFIG[props.source] ?? { ...FALLBACK, label: props.source }
})
</script>
