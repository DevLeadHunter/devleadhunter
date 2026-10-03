<template>
  <div
    class="min-h-screen bg-stone-100 font-[Inter,system-ui,sans-serif] text-base leading-relaxed text-neutral-900 antialiased"
  >
    <div class="h-1 bg-neutral-900" :style="{ backgroundColor: accentColor }" aria-hidden="true"></div>

    <header class="border-b border-stone-200 bg-white px-4 pt-6 pb-10 sm:px-6 sm:pb-14">
      <div class="mx-auto max-w-3xl">
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

        <div class="mt-8 text-center sm:mt-10">
          <p class="text-sm font-semibold tracking-[0.02em] text-neutral-500">{{ props.businessName }}</p>
          <h1
            class="mx-auto mt-3 max-w-[600px] text-[clamp(28px,5vw,40px)] leading-[1.15] font-semibold tracking-[-0.02em] text-balance"
          >
            {{ props.legalNotice.page_title }}
          </h1>
        </div>
      </div>
    </header>

    <main class="mx-auto flex max-w-3xl flex-col gap-12 px-4 py-10 sm:gap-14 sm:px-6 sm:py-14">
      <p
        v-if="props.legalNotice.demo_notice"
        class="rounded-xl border border-l-[3px] border-stone-200 border-l-neutral-900 bg-white px-6 py-5 text-[15px] text-neutral-700 sm:px-8"
        :style="{ borderLeftColor: accentColor }"
      >
        {{ props.legalNotice.demo_notice }}
      </p>

      <section
        v-for="section in props.legalNotice.sections"
        :id="section.anchor"
        :key="section.anchor"
        class="scroll-mt-6"
      >
        <h2 class="text-2xl leading-tight font-semibold tracking-[-0.01em]">{{ section.title }}</h2>
        <div class="mt-5 flex flex-col gap-4">
          <article
            v-for="block in section.blocks"
            :key="block.heading"
            class="rounded-xl border border-stone-200 bg-white p-6 sm:p-8"
          >
            <h3 class="text-lg leading-snug font-semibold">{{ block.heading }}</h3>
            <div class="mt-3 text-[15.5px] text-neutral-700">
              <p
                v-for="(line, lineIndex) in block.lines"
                :key="lineIndex"
                class="wrap-anywhere"
                :class="lineClasses(block, lineIndex)"
              >
                <span v-if="line.label" class="text-neutral-500">{{ line.label }}&nbsp;: </span>
                <a
                  v-if="line.href"
                  class="font-medium text-neutral-900 underline decoration-neutral-300 underline-offset-3 hover:decoration-current focus-visible:decoration-current"
                  :href="line.href"
                >
                  {{ line.text }}
                </a>
                <template v-else>{{ line.text }}</template>
              </p>
            </div>
          </article>
        </div>
      </section>
    </main>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { SiteLegalBlock, SiteLegalNotice } from '~/types/SiteLegalNotice'
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

/**
 * The classes of one line: an identity opens on its name in bold and keeps its lines tight, a text spaces its paragraphs.
 * @param block - The block the line belongs to.
 * @param lineIndex - The position of the line in its block.
 * @returns The classes of the line.
 */
function lineClasses(block: SiteLegalBlock, lineIndex: number): string {
  if (block.kind !== 'identity') {
    return 'mb-3 last:mb-0'
  }
  if (lineIndex === 0) {
    return 'mb-1 font-semibold text-neutral-900'
  }
  return 'mb-0.5 last:mb-0'
}

useHead({
  htmlAttrs: { lang: pageLanguage },
  title: pageTitle,
})
</script>
