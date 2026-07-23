<template>
  <div v-if="props.actIndex === 0" v-bind="$attrs" class="landing-card p-6 md:p-7">
    <p class="font-label text-[0.65rem] font-medium tracking-[0.18em] text-[#6b6355] uppercase">
      {{ $t('landing.story.visual.prospectLabel') }}
    </p>
    <div class="mt-5 flex items-start justify-between gap-4">
      <div class="min-w-0">
        <p class="font-display text-2xl font-semibold text-[#1b1813] md:text-3xl">
          {{ $t('landing.story.visual.prospectName') }}
        </p>
        <p class="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-[#6b6355]">
          <span>{{ $t('landing.story.visual.prospectCity') }}</span>
          <span class="text-[#6b6355]/40" aria-hidden="true">·</span>
          <span>{{ $t('landing.story.visual.prospectRating') }}</span>
          <span class="text-[#6b6355]/40" aria-hidden="true">·</span>
          <span>{{ $t('landing.story.visual.prospectReviews') }}</span>
        </p>
      </div>
      <span
        class="font-label inline-block shrink-0 -rotate-6 rounded border-2 border-[#bf4d33] px-2.5 py-1 text-[0.65rem] font-medium tracking-[0.14em] text-[#bf4d33] uppercase"
      >
        {{ $t('landing.story.visual.prospectStamp') }}
      </span>
    </div>
    <div class="mt-6 border-t border-dashed border-[#e3dccd] pt-4">
      <p class="inline-flex items-center gap-2 text-sm text-[#1b1813]">
        <i class="fa-solid fa-check text-xs text-[#2f7d4e]" aria-hidden="true"></i>
        {{ $t('landing.story.visual.prospectEmail') }}
      </p>
    </div>
  </div>

  <div v-else-if="props.actIndex === 1" v-bind="$attrs" class="landing-card overflow-hidden">
    <div class="flex items-center gap-2 border-b border-[#e3dccd] px-4 py-3">
      <span class="h-2.5 w-2.5 rounded-full bg-[#e3dccd]" aria-hidden="true"></span>
      <span class="h-2.5 w-2.5 rounded-full bg-[#e3dccd]" aria-hidden="true"></span>
      <span class="h-2.5 w-2.5 rounded-full bg-[#e3dccd]" aria-hidden="true"></span>
      <span
        class="font-label ml-2 flex-1 truncate rounded-full bg-[#f6f3ec] px-3 py-1 text-center text-[0.7rem] text-[#1b1813]"
      >
        {{ $t('landing.story.visual.siteUrl') }}
      </span>
    </div>
    <div class="p-6 md:p-7">
      <p class="font-display text-2xl font-semibold text-[#1b1813]">
        {{ $t('landing.story.visual.siteTitle') }}
      </p>
      <p class="mt-1 text-sm text-[#6b6355]">{{ $t('landing.story.visual.siteTagline') }}</p>
      <span class="mt-4 inline-flex rounded-full bg-[#1b1813] px-4 py-1.5 text-xs font-semibold text-[#fcfaf5]">
        {{ $t('landing.story.visual.siteCta') }}
      </span>
      <div class="mt-6 grid grid-cols-3 gap-2" aria-hidden="true">
        <div class="h-14 rounded-lg bg-[#ece5d8]"></div>
        <div class="h-14 rounded-lg border border-[#e3dccd] bg-[#f6f3ec]"></div>
        <div class="h-14 rounded-lg bg-[#ece5d8]"></div>
      </div>
      <p
        class="font-label mt-5 inline-flex items-center gap-1.5 rounded-full border border-[#e3dccd] bg-[#f6f3ec] px-2.5 py-1 text-[0.65rem] text-[#6b6355]"
      >
        <i class="fa-solid fa-pen text-[0.55rem] text-[#e8a33c]" aria-hidden="true"></i>
        {{ $t('landing.story.visual.siteChip') }}
      </p>
    </div>
  </div>

  <div v-else-if="props.actIndex === 2" v-bind="$attrs" class="landing-card p-6 md:p-7">
    <p class="font-label text-[0.65rem] font-medium tracking-[0.18em] text-[#6b6355] uppercase">
      {{ $t('landing.story.visual.emailLabel') }}
    </p>
    <p class="mt-5 text-base font-semibold text-[#1b1813] md:text-lg">
      {{ $t('landing.story.visual.emailSubject') }}
    </p>
    <p class="mt-3 text-sm leading-relaxed text-[#6b6355]">
      {{ $t('landing.story.visual.emailPreview') }}
    </p>
    <p class="mt-4">
      <span class="font-label text-xs text-[#1b1813] underline decoration-[#1b1813]/40 underline-offset-4">
        {{ $t('landing.story.visual.siteUrl') }}
      </span>
    </p>
    <p
      class="font-label mt-6 border-t border-dashed border-[#e3dccd] pt-4 text-[0.65rem] tracking-[0.14em] text-[#6b6355] uppercase"
    >
      {{ $t('landing.story.visual.emailMeta') }}
    </p>
  </div>

  <div v-else v-bind="$attrs" class="landing-card p-6 md:p-7">
    <p class="font-label text-[0.65rem] font-medium tracking-[0.18em] text-[#6b6355] uppercase">
      {{ $t('landing.story.visual.saleLabel') }}
    </p>
    <div class="mt-5 flex items-baseline gap-3">
      <p class="font-display text-5xl font-semibold text-[#2f7d4e]">
        {{ $t('landing.story.visual.saleAmount') }}
      </p>
      <p class="inline-flex items-center gap-1.5 text-sm font-medium text-[#1b1813]">
        <i class="fa-solid fa-circle-check text-xs text-[#2f7d4e]" aria-hidden="true"></i>
        {{ $t('landing.story.visual.saleStatus') }}
      </p>
    </div>
    <ul class="mt-6 space-y-3 border-t border-dashed border-[#e3dccd] pt-4">
      <li class="inline-flex items-center gap-2 text-sm text-[#1b1813]">
        <i class="fa-solid fa-check text-xs text-[#e8a33c]" aria-hidden="true"></i>
        {{ $t('landing.story.visual.saleDeploy') }}
      </li>
      <li class="inline-flex items-center gap-2 text-sm text-[#1b1813]">
        <i class="fa-solid fa-check text-xs text-[#e8a33c]" aria-hidden="true"></i>
        {{ $t('landing.story.visual.saleHandover') }}
      </li>
    </ul>
  </div>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { LandingStoryVisualProps, LandingStoryActIndex } from '~/types/LandingStoryVisual'

// Les commentaires entre les branches racines v-if rendent l'héritage d'attributs
// incohérent entre SSR et client → héritage explicite via v-bind="$attrs".
defineOptions({ inheritAttrs: false })

/** Landing story act visual for the pipeline narrative section. */
const props: LandingStoryVisualProps = defineProps({
  actIndex: {
    type: Number as PropType<LandingStoryActIndex>,
    required: true,
  },
})
</script>
