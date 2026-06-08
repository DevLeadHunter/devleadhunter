<template>
  <div class="plumber-site" :style="cssVars">
    <!-- Nav -->
    <nav class="fixed inset-x-0 top-0 z-50 border-b border-white/10 backdrop-blur-md" :style="{ backgroundColor: `${theme.secondary}ee` }">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <span class="text-lg font-bold text-white">{{ hero.title || businessName }}</span>
        <a
          v-if="hero.phone"
          :href="`tel:${hero.phone}`"
          class="hidden rounded-full px-5 py-2 text-sm font-semibold text-white shadow-lg transition hover:scale-105 sm:inline-flex"
          :style="{ backgroundColor: theme.accent }"
        >
          {{ hero.cta_label || 'Appeler' }}
        </a>
      </div>
    </nav>

    <HeroSection :hero="hero" :theme="theme" :business-name="businessName" />
    <TrustSection :trust="trust" :theme="theme" />
    <ServicesSection :services="services" :theme="theme" />
    <WhyUsSection :why-us="whyUs" :theme="theme" />
    <ContactSection :contact="contact" :theme="theme" />

    <footer class="border-t border-slate-200 bg-slate-50 px-6 py-8 text-center text-xs text-slate-500">
      © {{ new Date().getFullYear() }} {{ hero.title || businessName }} · Propulsé par DevLeadHunter
    </footer>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import { defaultTheme } from './types'
import type { Theme, HeroBlock, TrustBlock, ServicesBlock, WhyUsBlock, ContactBlock } from './types'
import HeroSection from './sections/HeroSection.vue'
import TrustSection from './sections/TrustSection.vue'
import ServicesSection from './sections/ServicesSection.vue'
import WhyUsSection from './sections/WhyUsSection.vue'
import ContactSection from './sections/ContactSection.vue'

const props = defineProps<{
  content: Record<string, unknown>
  businessName: string
}>()

type Block = Record<string, unknown>

const theme: ComputedRef<Theme> = computed((): Theme => {
  const raw = props.content.theme
  if (raw && typeof raw === 'object') {
    const t = raw as Record<string, string>
    return {
      primary: t.primary || defaultTheme.primary,
      secondary: t.secondary || defaultTheme.secondary,
      accent: t.accent || defaultTheme.accent,
    }
  }
  return defaultTheme
})

const cssVars = computed(() => ({
  '--color-primary': theme.value.primary,
  '--color-secondary': theme.value.secondary,
  '--color-accent': theme.value.accent,
}))

const blocks: ComputedRef<Block[]> = computed((): Block[] => {
  const body = props.content.body
  return Array.isArray(body) ? (body as Block[]) : []
})

const findBlock = (component: string): Block =>
  blocks.value.find((b: Block): boolean => b.component === component) ?? {}

const hero = computed(() => findBlock('hero') as HeroBlock)
const trust = computed(() => findBlock('trust') as TrustBlock)
const services = computed(() => findBlock('services') as ServicesBlock)
const whyUs = computed(() => findBlock('why_us') as WhyUsBlock)
const contact = computed(() => findBlock('contact') as ContactBlock)
</script>
