<template>
  <section class="mt-10 [counter-increment:legal-section]">
    <h2 class="font-display flex items-baseline gap-3 text-xl font-semibold text-[#1b1813] md:text-2xl">
      <span
        class="font-label shrink-0 text-sm font-medium text-[#6b6355] before:content-[counter(legal-section,decimal-leading-zero)]"
        aria-hidden="true"
      ></span>
      {{ $t(props.titleKey) }}
    </h2>
    <div class="mt-3 grid gap-3 border-t border-[#e3dccd] pt-4 text-base leading-relaxed text-[#6b6355]">
      <slot />
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { LandingLegalSectionProps } from '~/types/LandingLegalSection'

/** Numbered by the `legal-section` CSS counter that LandingLegalDocument resets: use it inside that component. */
const props: LandingLegalSectionProps = defineProps({
  titleKey: {
    type: String,
    required: true,
  },
})
</script>
