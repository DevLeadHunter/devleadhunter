<template>
  <section id="features" class="relative overflow-hidden bg-[#1b1813] px-5 py-24 md:px-8 md:py-36">
    <LandingAsterisk
      class="pointer-events-none absolute -top-20 -right-16 rotate-12 text-[13rem] text-[#e8a33c]/[0.08]"
    />

    <div class="relative mx-auto max-w-6xl">
      <p v-reveal class="landing-eyebrow landing-eyebrow--inverse">{{ $t('landing.features.eyebrow') }}</p>
      <h2
        v-reveal="{ delay: 80 }"
        class="font-display mt-6 max-w-2xl text-4xl leading-[1.06] font-semibold tracking-[-0.015em] text-[#fcfaf5] md:text-5xl"
      >
        {{ $t('landing.features.title') }}
      </h2>

      <div class="mt-14 grid gap-4 sm:grid-cols-2">
        <article
          v-for="(feature, index) in features"
          :key="feature.titleKey"
          v-reveal="{ delay: index * 60 }"
          class="landing-tilt rounded-2xl border border-[#3a342b] bg-[#262119] p-8 md:p-10"
        >
          <p class="font-label text-xs font-medium text-[#e8a33c]/80">0{{ index + 1 }}</p>
          <h3 class="font-display mt-4 text-xl font-semibold text-[#fcfaf5] md:text-2xl">
            {{ $t(feature.titleKey) }}
          </h3>
          <p class="mt-3 text-base leading-relaxed text-[#f6f3ec]/60">
            {{ $t(feature.descriptionKey) }}
          </p>
        </article>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
/** One capability shown in the feature grid. */
type LandingFeatureItem = {
  /** i18n key of the feature title. */
  titleKey: string
  /** i18n key of the feature description. */
  descriptionKey: string
}

/** The four capabilities highlighted under the deep-dive sections. */
const features: LandingFeatureItem[] = [
  {
    titleKey: 'landing.features.deliverability.title',
    descriptionKey: 'landing.features.deliverability.description',
  },
  {
    titleKey: 'landing.features.platforms.title',
    descriptionKey: 'landing.features.platforms.description',
  },
  {
    titleKey: 'landing.features.analytics.title',
    descriptionKey: 'landing.features.analytics.description',
  },
  {
    titleKey: 'landing.features.security.title',
    descriptionKey: 'landing.features.security.description',
  },
]
</script>
