<template>
  <div
    class="mx-auto grid max-w-6xl gap-8 px-5 pt-10 pb-24 md:px-8 md:pt-16 md:pb-32 lg:grid-cols-[15rem_minmax(0,1fr)] lg:gap-16"
  >
    <aside class="grid min-w-0 content-start gap-4 lg:sticky lg:top-28 lg:gap-7 lg:self-start">
      <p class="font-label text-[0.68rem] font-medium tracking-[0.16em] text-[#6b6355] uppercase">
        {{ $t('legal.nav.label') }}
      </p>
      <nav
        :aria-label="$t('legal.nav.label')"
        class="-mx-5 flex [scrollbar-width:none] gap-2 overflow-x-auto px-5 pb-1 md:-mx-8 md:px-8 lg:mx-0 lg:flex-col lg:gap-0 lg:overflow-visible lg:px-0 lg:pb-0"
      >
        <NuxtLink
          v-for="legalDocument in LEGAL_DOCUMENTS"
          :key="legalDocument.id"
          :to="localePath(legalDocument.path)"
          :aria-current="legalDocument.id === props.documentId ? 'page' : undefined"
          class="shrink-0 rounded-full border px-4 py-2 text-sm font-medium whitespace-nowrap transition-colors lg:rounded-none lg:border-0 lg:border-l-2 lg:px-0 lg:py-2.5 lg:pl-4 lg:whitespace-normal"
          :class="
            legalDocument.id === props.documentId
              ? 'border-[#1b1813] bg-[#1b1813] text-[#fcfaf5] lg:border-[#e8a33c] lg:bg-transparent lg:font-semibold lg:text-[#1b1813]'
              : 'border-[#e3dccd] text-[#6b6355] hover:text-[#1b1813]'
          "
        >
          {{ $t(legalDocument.labelKey) }}
        </NuxtLink>
      </nav>
      <div class="hidden content-start gap-1.5 border-t border-[#e3dccd] pt-6 text-sm lg:grid">
        <p class="font-label mb-1 text-[0.68rem] font-medium tracking-[0.16em] text-[#6b6355] uppercase">
          {{ $t('legal.nav.helpLabel') }}
        </p>
        <a
          :href="PUBLISHER_CONTACT.phoneHref"
          class="justify-self-start font-medium text-[#1b1813] tabular-nums transition-colors hover:text-[#6b6355]"
          @click="track('site_contact_phone_click', { location: 'legal_pages' })"
        >
          {{ $t('publisher.phone') }}
        </a>
        <a
          :href="PUBLISHER_CONTACT.emailHref"
          class="justify-self-start font-medium text-[#1b1813] transition-colors hover:text-[#6b6355]"
          @click="track('site_contact_email_click', { location: 'legal_pages' })"
        >
          {{ PUBLISHER_CONTACT.email }}
        </a>
        <NuxtLink :to="localePath('/contact')" class="landing-link mt-2 justify-self-start">
          {{ $t('legal.nav.helpLink') }}
        </NuxtLink>
      </div>
    </aside>

    <article class="max-w-3xl min-w-0 [counter-reset:legal-section]">
      <p class="landing-eyebrow">{{ $t('legal.updated') }}</p>
      <h1
        class="font-display mt-6 text-4xl leading-[1.06] font-semibold tracking-[-0.015em] text-[#1b1813] md:text-5xl"
      >
        {{ $t(props.titleKey) }}
      </h1>
      <p class="mt-6 max-w-2xl text-lg leading-relaxed text-[#6b6355]">{{ $t(props.introKey) }}</p>
      <slot />
    </article>
  </div>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { LandingLegalDocumentProps, LegalDocumentId } from '~/types/LandingLegalDocument'
import { LEGAL_DOCUMENTS } from '~/constants/legalDocuments'
import { PUBLISHER_CONTACT } from '~/constants/publisher'

const props: LandingLegalDocumentProps = defineProps({
  documentId: {
    type: String as PropType<LegalDocumentId>,
    required: true,
  },
  titleKey: {
    type: String,
    required: true,
  },
  introKey: {
    type: String,
    required: true,
  },
})

const localePath: ReturnType<typeof useLocalePath> = useLocalePath()
const { track }: { track: (event: string, properties?: Record<string, unknown> | undefined) => void } =
  useSiteTracking()
</script>
