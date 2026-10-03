<template>
  <div class="font-legal text-legal-ink flex min-h-screen flex-col bg-white text-base leading-6 antialiased">
    <header class="border-legal-line border-b bg-white px-4 sm:px-8">
      <div class="mx-auto flex h-16 max-w-[1280px] items-center justify-between gap-4 sm:h-[72px] sm:gap-6">
        <a class="flex min-w-0 items-center gap-2.5" :href="props.pagePaths.home">
          <img v-if="props.logoUrl" :src="props.logoUrl" alt="" class="h-8 w-8 shrink-0 rounded-md object-contain" />
          <span class="truncate text-lg leading-7 font-medium">{{ props.businessName }}</span>
        </a>
        <a
          class="shrink-0 rounded-lg border border-transparent px-4 py-2 text-[15px] leading-6 font-medium transition-opacity hover:opacity-90 focus-visible:opacity-90 sm:px-5 sm:py-3"
          :style="backToSiteButtonStyle"
          :href="props.pagePaths.home"
        >
          Retour au site
        </a>
      </div>
    </header>

    <main v-if="currentSection" class="flex flex-1 flex-col">
      <section class="px-6 pt-14 pb-12 sm:px-8 sm:pt-[88px] sm:pb-16">
        <div class="mx-auto grid w-full max-w-3xl justify-items-center gap-5 text-center">
          <nav aria-label="Fil d'Ariane">
            <ol class="text-legal-ink-soft flex items-center gap-2 text-sm leading-5">
              <li>
                <a
                  class="hover:text-legal-ink focus-visible:text-legal-ink transition-colors"
                  :href="props.pagePaths.home"
                >
                  Accueil
                </a>
              </li>
              <li aria-hidden="true">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="m9 18 6-6-6-6" />
                </svg>
              </li>
              <li class="text-legal-ink" aria-current="page">{{ currentSection.title }}</li>
            </ol>
          </nav>
          <h1 class="text-[32px] leading-[1.15] font-medium tracking-[-0.01em] text-balance sm:text-[40px]">
            {{ currentSection.title }}
          </h1>
          <p class="text-legal-ink-muted max-w-[600px] text-[17px] leading-7 text-balance">
            {{ currentSection.intro }}
          </p>
        </div>
      </section>

      <section class="bg-legal-band flex-1 px-4 py-12 sm:px-8 sm:py-16 lg:py-20">
        <div class="mx-auto flex w-full max-w-3xl flex-col gap-6">
          <article
            v-if="props.legalNotice.demo_notice"
            class="border-legal-line text-legal-ink-muted grid gap-4 rounded-xl border bg-white p-6 leading-[26px] sm:p-8"
          >
            <h2 class="text-legal-ink text-xl leading-7 font-medium">Site de démonstration</h2>
            <p>{{ props.legalNotice.demo_notice }}</p>
          </article>

          <article
            v-for="block in currentSection.blocks"
            :key="block.heading"
            class="border-legal-line text-legal-ink-muted grid gap-4 rounded-xl border bg-white p-6 leading-[26px] sm:p-8"
          >
            <h2 class="text-legal-ink text-xl leading-7 font-medium">{{ block.heading }}</h2>
            <p v-if="block.intro">{{ block.intro }}</p>
            <template v-if="block.kind === 'identity'">
              <p
                v-for="(paragraph, paragraphIndex) in identityParagraphs(block)"
                :key="paragraphIndex"
                class="wrap-anywhere"
              >
                <template v-for="(line, lineIndex) in paragraph" :key="lineIndex">
                  <br v-if="lineIndex > 0" />
                  <strong v-if="paragraphIndex === 0 && lineIndex === 0" class="font-bold">{{ line.text }}</strong>
                  <template v-else>
                    <template v-if="line.label">{{ line.label }}&nbsp;: </template>
                    <a
                      v-if="line.href"
                      class="font-medium underline underline-offset-2"
                      :style="{ color: linkColor }"
                      :href="line.href"
                    >
                      {{ line.text }}
                    </a>
                    <template v-else>{{ line.text }}</template>
                  </template>
                </template>
              </p>
            </template>
            <template v-else>
              <p v-for="(line, lineIndex) in block.lines" :key="lineIndex" class="wrap-anywhere">
                <a
                  v-if="line.href"
                  class="font-medium underline underline-offset-2"
                  :style="{ color: linkColor }"
                  :href="line.href"
                >
                  {{ line.text }}
                </a>
                <template v-else>{{ line.text }}</template>
              </p>
            </template>
          </article>
        </div>
      </section>
    </main>

    <footer class="border-legal-line bg-legal-band border-t px-6 py-6 sm:px-8">
      <div
        class="text-legal-ink-muted mx-auto flex max-w-[1280px] flex-col gap-3 text-sm leading-5 sm:flex-row sm:items-center sm:justify-between"
      >
        <p>© {{ currentYear }} {{ props.businessName }} · Tous droits réservés</p>
        <nav class="flex flex-wrap gap-x-6 gap-y-2" aria-label="Informations légales">
          <a
            v-for="legalSection in props.legalNotice.sections"
            :key="legalSection.page"
            class="hover:text-legal-ink focus-visible:text-legal-ink transition-colors"
            :class="{ 'text-legal-ink': legalSection.page === props.page }"
            :aria-current="legalSection.page === props.page ? 'page' : undefined"
            :href="props.pagePaths[legalSection.page]"
          >
            {{ legalSection.title }}
          </a>
        </nav>
      </div>
    </footer>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { RgbaColor } from '~/types/BackgroundTone'
import type {
  SiteLegalBlock,
  SiteLegalLine,
  SiteLegalNotice,
  SiteLegalPageKind,
  SiteLegalSection,
} from '~/types/SiteLegalNotice'
import type { SiteLegalPagePaths, SiteLegalPageProps } from '~/types/SiteLegalPage'
import { BackgroundToneUtils } from '~/utils/BackgroundToneUtils'

const DEFAULT_ACTION_COLOR: string = 'var(--color-legal-ink)'
const LIGHT_TEXT_COLOR: string = '#ffffff'

const props: SiteLegalPageProps = defineProps({
  legalNotice: {
    type: Object as PropType<SiteLegalNotice>,
    required: true,
  },
  page: {
    type: String as PropType<SiteLegalPageKind>,
    required: true,
  },
  businessName: {
    type: String,
    required: true,
  },
  logoUrl: {
    type: String as PropType<string | null>,
    default: null,
  },
  pagePaths: {
    type: Object as PropType<SiteLegalPagePaths>,
    required: true,
  },
})

const currentYear: number = new Date().getFullYear()

const currentSection: ComputedRef<SiteLegalSection | undefined> = computed((): SiteLegalSection | undefined =>
  props.legalNotice.sections.find((section: SiteLegalSection): boolean => section.page === props.page),
)

const accentColor: ComputedRef<RgbaColor | null> = computed((): RgbaColor | null =>
  props.legalNotice.accent_color ? BackgroundToneUtils.fromHex(props.legalNotice.accent_color) : null,
)

const isAccentReadableOnWhite: ComputedRef<boolean> = computed(
  (): boolean => accentColor.value !== null && BackgroundToneUtils.prefersLightInk(accentColor.value),
)

const linkColor: ComputedRef<string> = computed((): string =>
  isAccentReadableOnWhite.value && props.legalNotice.accent_color
    ? props.legalNotice.accent_color
    : DEFAULT_ACTION_COLOR,
)

const backToSiteButtonStyle: ComputedRef<Record<string, string>> = computed((): Record<string, string> => {
  if (!accentColor.value || !props.legalNotice.accent_color) {
    return { backgroundColor: DEFAULT_ACTION_COLOR, color: LIGHT_TEXT_COLOR }
  }
  return {
    backgroundColor: props.legalNotice.accent_color,
    color: isAccentReadableOnWhite.value ? LIGHT_TEXT_COLOR : DEFAULT_ACTION_COLOR,
  }
})

const pageTitle: ComputedRef<string> = computed(
  (): string => `${currentSection.value?.title ?? props.legalNotice.page_title} · ${props.businessName}`,
)

const pageLanguage: ComputedRef<string> = computed((): string => props.legalNotice.locale)

/**
 * The lines of an identity grouped by paragraph, in their order: name and address, then contacts, then identifiers.
 * @param block - An identity block.
 * @returns One list of lines per paragraph.
 */
function identityParagraphs(block: SiteLegalBlock): SiteLegalLine[][] {
  return block.lines.reduce((paragraphs: SiteLegalLine[][], line: SiteLegalLine): SiteLegalLine[][] => {
    const lastParagraph: SiteLegalLine[] | undefined = paragraphs.at(-1)
    if (lastParagraph && lastParagraph[0]?.paragraph === line.paragraph) {
      lastParagraph.push(line)
    } else {
      paragraphs.push([line])
    }
    return paragraphs
  }, [])
}

useHead({
  htmlAttrs: { lang: pageLanguage },
  title: pageTitle,
})
</script>
