<template>
  <div>
    <LandingHero @discover="scrollToSection('#how-it-works')" />
    <LandingPipeline />
    <LandingFeatures />
    <LandingPlatforms />
    <LandingPricing :settings="creditSettings" :loading="isLoading" />
    <LandingFaq />
    <LandingCta />
  </div>
</template>

<script setup lang="ts">
import type { CreditSettings } from '~/types'
import type { Ref } from 'vue'
import { ref, onMounted } from 'vue'
import * as creditSettingsService from '~/services/creditSettingsService'

/**
 * Landing page — marketing presentation of DevLeadHunter.
 * Composes the hero, automation pipeline, feature deep-dives, platforms,
 * pricing, FAQ and final call-to-action.
 */
definePageMeta({
  layout: 'marketing',
  // Desktop app: skip the landing and go to the dashboard (web keeps the landing).
  middleware: ['desktop-redirect'],
})

const { t } = useI18n()

/** Credit settings fetched from the API (null while loading or on error). */
const creditSettings: Ref<CreditSettings | null> = ref<CreditSettings | null>(null)

/** Whether the credit settings request is in flight. */
const isLoading: Ref<boolean> = ref<boolean>(true)

/**
 * Load credit settings from the API for the pricing section.
 */
async function loadCreditSettings(): Promise<void> {
  try {
    isLoading.value = true
    creditSettings.value = await creditSettingsService.getCreditSettings()
  } catch (error) {
    console.error('Failed to load credit settings:', error)
  } finally {
    isLoading.value = false
  }
}

/**
 * Smooth-scroll to a section, accounting for the sticky header height.
 * @param selector - CSS selector of the target section.
 */
function scrollToSection(selector: string): void {
  const element: Element | null = document.querySelector(selector)
  if (element) {
    const headerOffset = 80
    const elementPosition: number = element.getBoundingClientRect().top
    const offsetPosition: number = elementPosition + window.pageYOffset - headerOffset
    window.scrollTo({ top: offsetPosition, behavior: 'smooth' })
  }
}

onMounted(async (): Promise<void> => {
  await loadCreditSettings()
})

// SEO meta
useHead({
  title: (): string => `DevLeadHunter — ${t('hero.title')} ${t('hero.titleHighlight')}`,
  meta: [
    {
      name: 'description',
      content: (): string => t('hero.subtitle'),
    },
  ],
})
</script>
