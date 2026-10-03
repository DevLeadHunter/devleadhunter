<template>
  <div
    ref="footerElement"
    data-dlh-legal-footer
    class="flex justify-center border-t px-4 pt-[18px] pb-[calc(18px+env(safe-area-inset-bottom))] font-[Inter,system-ui,sans-serif] text-[13px] leading-normal tracking-[0.01em] max-md:pb-[calc(112px+env(safe-area-inset-bottom))]"
    :class="{
      'border-black/10 text-black/65': !hasLightInk && !hasFullInk,
      'border-black/10 text-neutral-900': !hasLightInk && hasFullInk,
      'border-white/10 text-white/70': hasLightInk && !hasFullInk,
      'border-white/10 text-white': hasLightInk && hasFullInk,
    }"
    :style="backgroundStyle"
  >
    <nav
      class="flex flex-wrap items-center justify-center gap-x-2.5 gap-y-1 text-center"
      aria-label="Informations légales"
    >
      <template v-for="(link, index) in props.legalNotice.links" :key="link.anchor">
        <span v-if="index > 0" class="opacity-70" aria-hidden="true">·</span>
        <a
          class="underline-offset-3 transition-colors hover:underline focus-visible:underline"
          :class="
            hasLightInk
              ? 'hover:text-white focus-visible:text-white'
              : 'hover:text-neutral-900 focus-visible:text-neutral-900'
          "
          :href="SiteLegalLinkUtils.sectionHref(props.legalPagePath, link.anchor)"
        >
          {{ link.label }}
        </a>
      </template>
    </nav>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import type { RgbaColor } from '~/types/BackgroundTone'
import type { SiteLegalFooterProps } from '~/types/SiteLegalFooter'
import type { SiteLegalNotice } from '~/types/SiteLegalNotice'
import { BackgroundToneUtils } from '~/utils/BackgroundToneUtils'
import { SiteLegalLinkUtils } from '~/utils/SiteLegalLinkUtils'

const props: SiteLegalFooterProps = defineProps({
  legalNotice: {
    type: Object as PropType<SiteLegalNotice>,
    required: true,
  },
  legalPagePath: {
    type: String,
    required: true,
  },
})

const footerElement: Ref<HTMLElement | null> = ref(null)
const templateBackground: Ref<RgbaColor | null> = ref(null)

const hasLightInk: ComputedRef<boolean> = computed(
  (): boolean => templateBackground.value !== null && BackgroundToneUtils.prefersLightInk(templateBackground.value),
)

const hasFullInk: ComputedRef<boolean> = computed(
  (): boolean => templateBackground.value !== null && BackgroundToneUtils.needsFullInk(templateBackground.value),
)

const backgroundStyle: ComputedRef<Record<string, string>> = computed((): Record<string, string> => {
  const color: RgbaColor | null = templateBackground.value
  return color ? { backgroundColor: `rgb(${color.red}, ${color.green}, ${color.blue})` } : {}
})

/** Read the colour the template paints right above the strip, so the strip continues it. */
function readTemplateBackground(): void {
  const previous: Element | null | undefined = footerElement.value?.previousElementSibling
  if (previous instanceof HTMLElement) {
    templateBackground.value = BackgroundToneUtils.bottomBackground(previous)
  }
}

onMounted((): void => {
  readTemplateBackground()
  if (document.readyState !== 'complete') {
    window.addEventListener('load', readTemplateBackground, { once: true })
  }
})
</script>
