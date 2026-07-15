<template>
  <section id="pricing" class="px-5 py-24 md:px-8 md:py-36">
    <div class="mx-auto max-w-6xl">
      <div class="mx-auto max-w-2xl text-center">
        <p v-reveal class="landing-eyebrow">{{ $t('landing.pricing.eyebrow') }}</p>
        <h2
          v-reveal="{ delay: 80 }"
          class="font-display mt-6 text-4xl leading-[1.06] font-semibold tracking-[-0.015em] text-[#1b1813] md:text-5xl"
        >
          {{ $t('landing.pricing.title') }}
        </h2>
        <p v-reveal="{ delay: 160 }" class="mt-5 text-lg leading-relaxed text-[#6b6355]">
          {{ $t('landing.pricing.subtitle') }}
        </p>
      </div>

      <div
        v-reveal="{ delay: 220 }"
        class="landing-card mx-auto mt-14 max-w-3xl overflow-hidden md:grid md:grid-cols-2"
      >
        <!-- ROI pull-quote + CTA -->
        <div class="flex flex-col justify-between gap-10 p-8 md:border-r md:border-[#e3dccd] md:p-10">
          <blockquote class="font-display text-2xl leading-snug font-medium text-[#1b1813] italic md:text-[1.7rem]">
            «&nbsp;{{ $t('landing.pricing.roiNote') }}&nbsp;»
          </blockquote>
          <div>
            <NuxtLink
              :to="localePath('/signup')"
              class="landing-btn-primary w-full text-center md:w-auto"
              @click="track('site_cta_click', { location: 'pricing', label: 'signup' })"
            >
              {{ $t('landing.pricing.cta') }}
            </NuxtLink>
          </div>
        </div>

        <!-- Credit stats -->
        <div class="bg-[#f6f3ec]/60 p-8 md:p-10">
          <!-- Loading skeleton -->
          <div v-if="props.loading" class="space-y-6" aria-hidden="true">
            <div v-for="row in 4" :key="row" class="animate-pulse border-b border-dashed border-[#e3dccd] pb-5">
              <div class="h-7 w-16 rounded bg-[#e3dccd]"></div>
              <div class="mt-2 h-3 w-40 rounded bg-[#e3dccd]/70"></div>
            </div>
          </div>

          <!-- Stats -->
          <dl v-else-if="pricingStats.length > 0">
            <div
              v-for="(stat, index) in pricingStats"
              :key="stat.labelKey"
              class="border-dashed border-[#e3dccd] py-5 first:pt-0 last:pb-0"
              :class="index < pricingStats.length - 1 ? 'border-b' : ''"
            >
              <dt class="font-label order-2 text-[0.7rem] tracking-[0.14em] text-[#6b6355] uppercase">
                {{ $t(stat.labelKey) }}
              </dt>
              <dd class="font-display order-1 text-3xl font-semibold text-[#1b1813]">{{ stat.value }}</dd>
            </div>
          </dl>

          <!-- Load error -->
          <p v-else class="text-sm leading-relaxed text-[#6b6355]">
            {{ $t('landing.pricing.loadError') }}
          </p>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { PropType, ComputedRef } from 'vue'
import type { CreditSettings } from '~/types'
import type { LandingPricingProps } from '~/types/LandingPricing'
import { computed } from 'vue'

/**
 * Defines the component props.
 */
const props: LandingPricingProps = defineProps({
  settings: {
    // Nullable: Vue rejects `null` on a required Object prop, so use a default instead.
    type: Object as PropType<CreditSettings | null>,
    default: null,
  },
  loading: {
    type: Boolean,
    required: true,
  },
})

const { locale } = useI18n()
const localePath = useLocalePath()
const { track } = useSiteTracking()

/** One credit metric displayed in the pricing card. */
interface LandingPricingStat {
  /** Formatted value (count or price). */
  value: string
  /** i18n key of the metric label. */
  labelKey: string
}

/**
 * Format a price in EUR for the active locale.
 * @param value - Price in euros.
 * @returns Localized currency string (e.g. « 0,05 € »).
 */
function formatPrice(value: number): string {
  return new Intl.NumberFormat(locale.value, {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(value)
}

/** Credit metrics derived from the API settings (empty while unavailable). */
const pricingStats: ComputedRef<LandingPricingStat[]> = computed((): LandingPricingStat[] => {
  if (!props.settings) {
    return []
  }
  return [
    { value: String(props.settings.free_credits_on_signup), labelKey: 'landing.pricing.freeCredits' },
    { value: formatPrice(props.settings.price_per_credit), labelKey: 'landing.pricing.pricePerCredit' },
    { value: String(props.settings.credits_per_search), labelKey: 'landing.pricing.creditsPerSearch' },
    { value: String(props.settings.credits_per_email), labelKey: 'landing.pricing.creditsPerEmail' },
  ]
})
</script>
