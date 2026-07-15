<template>
  <div>
    <LandingHero @discover="scrollToSection('#how-it-works')" />
    <LandingPipelineStory />
    <LandingProductProof />
    <LandingSectionDivider />
    <LandingEmailCampaigns />
    <LandingSectionDivider />
    <LandingLeadScoring />
    <LandingSectionDivider />
    <LandingSaleAutomation />
    <LandingFeatureGrid />
    <LandingPricing :settings="creditSettings" :loading="isLoading" />
    <LandingSectionDivider />
    <LandingDesktopApp />
    <LandingSectionDivider />
    <LandingFaq />
    <LandingFinalCta />
  </div>
</template>

<script setup lang="ts">
import type { CreditSettings } from '~/types'
import type { Ref } from 'vue'
import { ref, onMounted } from 'vue'
import * as creditSettingsService from '~/services/creditSettingsService'

/**
 * Landing page — marketing presentation of DevLeadHunter.
 * Editorial light redesign: hero, pinned pipeline story, product proof,
 * feature grid, pricing, FAQ and final call-to-action.
 */
definePageMeta({
  layout: 'marketing',
  // Desktop app: skip the landing and go to the dashboard (web keeps the landing).
  middleware: ['desktop-redirect'],
})

const { t } = useI18n()
const { track } = useSiteTracking()

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

/**
 * Fire a `site_section_view` event the first time each landing section scrolls into view.
 */
function trackSectionViews(): void {
  if (typeof IntersectionObserver === 'undefined') return
  const seen: Set<string> = new Set<string>()
  const observer: IntersectionObserver = new IntersectionObserver(
    (entries: IntersectionObserverEntry[]): void => {
      for (const entry of entries) {
        const id: string = (entry.target as HTMLElement).id
        if (entry.isIntersecting && id && !seen.has(id)) {
          seen.add(id)
          track('site_section_view', { section: id })
          observer.unobserve(entry.target)
        }
      }
    },
    { threshold: 0.5 },
  )
  document.querySelectorAll('section[id]').forEach((element: Element): void => observer.observe(element))
}

onMounted(async (): Promise<void> => {
  trackSectionViews()
  await loadCreditSettings()
})

// SEO meta — localized title/description, social cards and JSON-LD.
// (canonical, hreflang alternates and <html lang> are set by the marketing layout)
useHead(() => ({
  title: t('landing.seo.title'),
  meta: [
    { name: 'description', content: t('landing.seo.description') },
    { property: 'og:title', content: t('landing.seo.title') },
    { property: 'og:description', content: t('landing.seo.description') },
    { property: 'og:type', content: 'website' },
    { name: 'twitter:title', content: t('landing.seo.title') },
    { name: 'twitter:description', content: t('landing.seo.description') },
  ],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'SoftwareApplication',
        name: 'DevLeadHunter',
        description: t('landing.seo.description'),
        applicationCategory: 'BusinessApplication',
        operatingSystem: 'Web, Windows, macOS',
        offers: {
          '@type': 'Offer',
          price: '0',
          priceCurrency: 'EUR',
          description: t('landing.hero.trust2'),
        },
        author: {
          '@type': 'Person',
          name: 'Léo Guillaume',
          url: 'https://dibodev.fr',
        },
      }),
    },
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'Organization',
        name: 'DevLeadHunter',
        url: 'https://devleadhunter.dibodev.fr',
        logo: 'https://devleadhunter.dibodev.fr/favicon.svg',
        founder: {
          '@type': 'Person',
          name: 'Léo Guillaume',
          url: 'https://dibodev.fr',
        },
      }),
    },
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        name: 'DevLeadHunter',
        url: 'https://devleadhunter.dibodev.fr',
        inLanguage: ['en-US', 'fr-FR'],
        publisher: {
          '@type': 'Organization',
          name: 'DevLeadHunter',
        },
      }),
    },
  ],
}))
</script>
