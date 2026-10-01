<template>
  <div>
    <section class="mx-auto max-w-6xl px-5 pt-14 md:px-8 md:pt-20">
      <p class="landing-eyebrow">{{ $t('contact.eyebrow') }}</p>
      <h1
        class="font-display mt-6 max-w-3xl text-[2.6rem] leading-[1.04] font-semibold tracking-[-0.02em] text-[#1b1813] md:text-6xl"
      >
        {{ $t('contact.titleStart') }}
        <em class="font-medium italic">{{ $t('contact.titleAccent') }}</em
        ><span class="text-[#e8a33c]" aria-hidden="true">.</span>
      </h1>
      <p class="mt-6 max-w-xl text-lg leading-relaxed text-[#6b6355] md:text-xl">{{ $t('contact.lead') }}</p>
    </section>

    <section
      class="mx-auto grid max-w-6xl gap-10 px-5 pt-10 pb-16 md:px-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] lg:gap-16 lg:pt-14 lg:pb-24"
    >
      <LandingContactChannels />
      <LandingContactForm />
    </section>

    <section class="mx-auto max-w-6xl px-5 pb-20 md:px-8 md:pb-28">
      <div class="border-t border-[#e3dccd] pt-10">
        <p class="font-label text-[0.68rem] font-medium tracking-[0.16em] text-[#6b6355] uppercase">
          {{ $t('contact.quick.label') }}
        </p>
        <ul class="mt-3 grid md:grid-cols-3 md:gap-8">
          <li v-for="questionKey in QUICK_QUESTION_KEYS" :key="questionKey">
            <NuxtLink
              :to="{ path: localePath('index'), hash: '#faq' }"
              class="font-display flex items-center justify-between gap-4 border-b border-[#e3dccd] py-4 text-lg font-medium text-[#1b1813] transition-colors hover:text-[#6b6355]"
              @click="track('site_nav_click', { target: '#faq', location: 'contact_quick_answers' })"
            >
              {{ $t(`contact.quick.${questionKey}`) }}
              <UIcon name="i-lucide-arrow-right" class="h-4 w-4 shrink-0" aria-hidden="true" />
            </NuxtLink>
          </li>
        </ul>
      </div>
    </section>
  </div>
</template>

<script lang="ts" setup>
definePageMeta({
  layout: 'marketing',
})

const { t }: { t: (key: string, params?: Record<string, unknown>) => string } = useI18n()
const localePath: ReturnType<typeof useLocalePath> = useLocalePath()
const { track }: { track: (event: string, properties?: Record<string, unknown> | undefined) => void } =
  useSiteTracking()

const QUICK_QUESTION_KEYS: string[] = ['credits', 'trial', 'privacy']

useHead(() => ({
  title: `${t('contact.meta.title')} — DevLeadHunter`,
  meta: [{ name: 'description', content: t('contact.meta.description') }],
}))
</script>
