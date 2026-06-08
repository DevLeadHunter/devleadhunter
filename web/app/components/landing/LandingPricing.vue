<template>
  <section id="pricing" class="scroll-mt-20 bg-[#050505] py-24 md:py-32">
    <div class="container mx-auto px-4 md:px-6 lg:px-8">
      <div class="mx-auto mb-16 max-w-2xl text-center">
        <div
          v-reveal
          class="mb-5 inline-flex items-center gap-2 rounded-full border border-[#2BAD5F]/30 bg-[#2BAD5F]/10 px-4 py-1.5"
        >
          <i class="fa-solid fa-tag text-xs text-[#3fb950]"></i>
          <span class="text-xs font-semibold tracking-wide text-[#3fb950] uppercase">{{ $t('nav.pricing') }}</span>
        </div>
        <h2 v-reveal class="mb-5 text-3xl font-bold tracking-tight text-[#f9f9f9] md:text-4xl lg:text-5xl">
          {{ $t('pricing.title') }}
        </h2>
        <p v-reveal class="text-base leading-relaxed text-[#8b949e] md:text-lg">{{ $t('pricing.subtitle') }}</p>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="mx-auto max-w-4xl">
        <div class="animate-pulse rounded-3xl border border-[#30363d] bg-[#0d1117] p-8">
          <div class="mb-4 h-6 w-1/3 rounded bg-[#21262d]"></div>
          <div class="mb-8 h-4 w-2/3 rounded bg-[#21262d]"></div>
          <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div v-for="n in 4" :key="n" class="h-20 rounded-xl bg-[#21262d]"></div>
          </div>
        </div>
      </div>

      <!-- Pricing card -->
      <div v-else-if="settings" v-reveal class="mx-auto max-w-4xl">
        <div class="overflow-hidden rounded-3xl border border-[#30363d] bg-[#0d1117]">
          <div class="border-b border-[#30363d] bg-[#161b22] p-7 md:p-9">
            <div class="flex flex-col items-start justify-between gap-5 md:flex-row md:items-center">
              <div>
                <h3 class="mb-1.5 text-xl font-bold text-[#f9f9f9] md:text-2xl">{{ $t('pricing.creditsTitle') }}</h3>
                <p class="text-sm text-[#8b949e]">{{ $t('pricing.creditsSubtitle') }}</p>
              </div>
              <div class="flex items-baseline gap-1.5 rounded-2xl border border-[#2BAD5F]/30 bg-[#2BAD5F]/10 px-5 py-3">
                <span class="text-3xl font-bold text-[#f9f9f9]">€{{ settings.price_per_credit.toFixed(2) }}</span>
                <span class="text-sm font-medium text-[#8b949e]"
                  >/ {{ $t('pricing.pricePerCredit').toLowerCase() }}</span
                >
              </div>
            </div>
          </div>

          <div class="p-7 md:p-9">
            <!-- Usage cards -->
            <div class="mb-8 grid grid-cols-1 gap-4 md:grid-cols-2">
              <div class="rounded-2xl border border-[#30363d] bg-[#161b22] p-5">
                <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-[#58a6ff]/10">
                  <i class="fa-solid fa-magnifying-glass text-[#58a6ff]"></i>
                </div>
                <h4 class="mb-1.5 text-base font-semibold text-[#f9f9f9]">{{ $t('pricing.search.title') }}</h4>
                <p class="text-sm leading-relaxed text-[#8b949e]">{{ $t('pricing.search.description') }}</p>
              </div>
              <div class="rounded-2xl border border-[#30363d] bg-[#161b22] p-5">
                <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-[#2BAD5F]/10">
                  <i class="fa-solid fa-paper-plane text-[#3fb950]"></i>
                </div>
                <h4 class="mb-1.5 text-base font-semibold text-[#f9f9f9]">{{ $t('pricing.email.title') }}</h4>
                <p class="text-sm leading-relaxed text-[#8b949e]">{{ $t('pricing.email.description') }}</p>
              </div>
            </div>

            <!-- Credit cost breakdown -->
            <div class="grid grid-cols-2 gap-4 border-t border-[#30363d] pt-8 md:grid-cols-4">
              <div class="text-center">
                <div class="mb-1 text-2xl font-bold text-[#f9f9f9]">{{ settings.credits_per_search }}</div>
                <div class="text-xs font-medium tracking-wide text-[#8b949e] uppercase">
                  {{ $t('pricing.creditsPerSearch') }}
                </div>
              </div>
              <div class="text-center">
                <div class="mb-1 text-2xl font-bold text-[#f9f9f9]">{{ settings.credits_per_result }}</div>
                <div class="text-xs font-medium tracking-wide text-[#8b949e] uppercase">
                  {{ $t('pricing.creditsPerResult') }}
                </div>
              </div>
              <div class="text-center">
                <div class="mb-1 text-2xl font-bold text-[#f9f9f9]">{{ settings.credits_per_email }}</div>
                <div class="text-xs font-medium tracking-wide text-[#8b949e] uppercase">
                  {{ $t('pricing.creditsPerEmail') }}
                </div>
              </div>
              <div class="text-center">
                <div class="mb-1 text-2xl font-bold text-[#f9f9f9]">{{ settings.minimum_credits_purchase }}</div>
                <div class="text-xs font-medium tracking-wide text-[#8b949e] uppercase">
                  {{ $t('pricing.minPurchase') }}
                </div>
              </div>
            </div>

            <!-- Free credits highlight + CTA -->
            <div
              class="mt-8 flex flex-col items-center justify-between gap-5 rounded-2xl border border-[#2BAD5F]/30 bg-[#2BAD5F]/[0.07] p-6 sm:flex-row"
            >
              <div class="text-center sm:text-left">
                <div class="flex items-center justify-center gap-2 sm:justify-start">
                  <i class="fa-solid fa-gift text-[#3fb950]"></i>
                  <span class="text-2xl font-bold text-[#3fb950]">{{ settings.free_credits_on_signup }}</span>
                  <span class="text-base font-medium text-[#f9f9f9]">{{ $t('pricing.freeCredits') }}</span>
                </div>
                <p class="mt-1.5 text-xs text-[#8b949e]">{{ $t('pricing.roiNote') }}</p>
              </div>
              <NuxtLink :to="localePath('/signup')" class="btn-emerald w-full py-3 text-sm sm:w-auto">
                {{ $t('cta.primary') }}<i class="fa-solid fa-arrow-right text-xs"></i>
              </NuxtLink>
            </div>
          </div>
        </div>
      </div>

      <!-- Error fallback -->
      <div v-else class="mx-auto max-w-2xl">
        <div class="rounded-2xl border border-[#30363d] bg-[#0d1117] p-8 text-center text-sm text-[#8b949e]">
          {{ $t('pricing.loadError') }}
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import { computed } from 'vue'
import type { CreditSettings } from '~/types'
import type { LandingPricingProps } from '~/types/LandingPricing'

/**
 * Pricing section presenting the pay-as-you-go credit model, fed by the API.
 */
const props: LandingPricingProps = defineProps({
  settings: {
    type: Object as PropType<CreditSettings | null>,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const localePath = useLocalePath()

/** Credit settings exposed to the template (null while loading or on error). */
const settings: ComputedRef<CreditSettings | null> = computed((): CreditSettings | null => props.settings)

/** Whether the credit settings are still loading. */
const loading: ComputedRef<boolean> = computed((): boolean => props.loading)
</script>
