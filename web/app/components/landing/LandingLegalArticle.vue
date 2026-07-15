<template>
  <article class="mx-auto max-w-3xl px-5 pt-14 pb-24 md:px-8 md:pt-20 md:pb-32">
    <p class="landing-eyebrow">{{ $t('legal.updated') }}</p>
    <h1 class="font-display mt-6 text-4xl leading-[1.06] font-semibold tracking-[-0.015em] text-[#1b1813] md:text-5xl">
      {{ $t(props.titleKey) }}
    </h1>
    <p class="mt-6 max-w-2xl text-lg leading-relaxed text-[#6b6355]">
      {{ $t(props.introKey) }}
    </p>

    <section v-for="(sectionKey, index) in props.sectionKeys" :key="sectionKey" class="mt-10">
      <h2 class="font-display text-xl font-semibold text-[#1b1813] md:text-2xl">
        <span class="font-label mr-3 text-sm font-medium text-[#6b6355]">0{{ index + 1 }}</span>
        {{ $t(`${sectionKey}.title`) }}
      </h2>
      <p class="mt-3 border-t border-[#e3dccd] pt-4 text-base leading-relaxed text-[#6b6355]">
        {{ $t(`${sectionKey}.body`) }}
      </p>
    </section>
  </article>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { LandingLegalArticleProps } from '~/types/LandingLegalArticle'

/**
 * Defines the component props.
 */
const props: LandingLegalArticleProps = defineProps({
  titleKey: {
    type: String,
    required: true,
  },
  introKey: {
    type: String,
    required: true,
  },
  sectionKeys: {
    type: Array as PropType<string[]>,
    required: true,
  },
})
</script>
