<template>
  <div
    class="min-h-screen bg-white font-[Inter,system-ui,sans-serif] text-base leading-relaxed text-neutral-900 antialiased"
  >
    <div class="h-1 bg-neutral-900" :style="{ backgroundColor: accentColor }" aria-hidden="true"></div>
    <div class="mx-auto max-w-[720px] px-4 pt-6 pb-14 sm:px-6 sm:pt-8 sm:pb-18">
      <a
        class="inline-flex items-center gap-2 text-sm font-medium text-neutral-600 underline-offset-3 hover:text-neutral-900 hover:underline focus-visible:underline"
        :href="props.siteHref"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M19 12H5" />
          <path d="m11 18-6-6 6-6" />
        </svg>
        Retour au site
      </a>

      <header class="mt-7 border-b border-stone-200 pb-7 sm:mt-10">
        <p class="text-sm font-semibold tracking-[0.02em] text-neutral-600">{{ props.businessName }}</p>
        <h1 class="mt-3 text-[clamp(28px,5vw,40px)] leading-[1.15] font-bold tracking-[-0.02em] text-balance">
          {{ props.legalNotice.page_title }}
        </h1>
      </header>

      <p
        v-if="props.legalNotice.demo_notice"
        class="mt-7 rounded-r-lg border-l-[3px] border-neutral-900 bg-stone-100 px-[18px] py-4 text-[15px]"
        :style="{ borderColor: accentColor }"
      >
        {{ props.legalNotice.demo_notice }}
      </p>

      <section
        v-for="section in props.legalNotice.sections"
        :id="section.anchor"
        :key="section.anchor"
        class="scroll-mt-4 pt-9 sm:pt-11"
      >
        <h2 class="text-2xl leading-tight font-bold tracking-[-0.01em]">{{ section.title }}</h2>
        <div v-for="block in section.blocks" :key="block.heading" class="mt-6">
          <h3 class="mb-1.5 text-[15px] leading-snug font-semibold">{{ block.heading }}</h3>
          <p
            v-for="(line, index) in block.lines"
            :key="index"
            class="text-[15.5px] wrap-anywhere"
            :class="block.kind === 'identity' ? 'mb-0.5' : 'mb-2.5'"
          >
            <span v-if="line.label" class="text-neutral-600">{{ line.label }}&nbsp;: </span>
            <a
              v-if="line.href"
              class="underline decoration-black/30 underline-offset-3 hover:decoration-current focus-visible:decoration-current"
              :href="line.href"
            >
              {{ line.text }}
            </a>
            <template v-else>{{ line.text }}</template>
          </p>
        </div>
      </section>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { SiteLegalNotice } from '~/types/SiteLegalNotice'
import type { SiteLegalPageProps } from '~/types/SiteLegalPage'

const props: SiteLegalPageProps = defineProps({
  legalNotice: {
    type: Object as PropType<SiteLegalNotice>,
    required: true,
  },
  businessName: {
    type: String,
    required: true,
  },
  siteHref: {
    type: String,
    required: true,
  },
})

const accentColor: ComputedRef<string | undefined> = computed(
  (): string | undefined => props.legalNotice.accent_color ?? undefined,
)

const pageLanguage: ComputedRef<string> = computed((): string => props.legalNotice.locale)

const pageTitle: ComputedRef<string> = computed((): string => `${props.legalNotice.page_title} · ${props.businessName}`)

useHead({
  htmlAttrs: { lang: pageLanguage },
  title: pageTitle,
})
</script>
