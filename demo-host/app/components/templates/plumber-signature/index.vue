<template>
  <div ref="root" class="sig" :style="cssVars">
    <!-- ════ Bandeau urgence — fin, très visible, sticky au-dessus du header ════ -->
    <div class="alertbar">
      <div class="alertbar-inner">
        <span class="alertbar-pulse" aria-hidden="true"></span>
        <span class="alertbar-text">Urgence plomberie&nbsp;? Intervention 24&nbsp;h/24 · 7&nbsp;j/7</span>
        <a v-if="phone" :href="`tel:${phoneHref}`" class="alertbar-phone">
          <svg viewBox="0 0 24 24" class="ico" aria-hidden="true" v-html="icon('phone')" />
          <span>{{ phone }}</span>
        </a>
      </div>
    </div>

    <!-- ════ Header ════ -->
    <header class="nav">
      <div class="nav-inner">
        <a href="#top" class="brand">
          <span class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24"><path class="brand-drop" d="M12 3c3 4 5 6.5 5 9a5 5 0 0 1-10 0c0-2.5 2-5 5-9Z" /></svg>
          </span>
          <span class="brand-name">{{ businessName }}</span>
        </a>
        <nav class="nav-links" aria-label="Navigation principale">
          <a href="#services">Services</a>
          <a href="#etapes">Déroulé</a>
          <a href="#realisations">Réalisations</a>
          <a href="#histoire">L'artisan</a>
          <a href="#faq">FAQ</a>
        </nav>
        <a href="#contact" class="nav-cta">Devis gratuit</a>
      </div>
    </header>

    <main id="top">
      <!-- ════ Hero ════ -->
      <HeroSection
        :hero="hero"
        :business-name="businessName"
        :city="city"
        :phone="phone"
        :phone-href="phoneHref"
        :hero-points="heroPoints"
        :hero-chip="heroChip"
        :marquee-words="marqueeWords"
      />

      <!-- ════ Stats / confiance ════ -->
      <StatsSection v-if="trustItems.length" :trust-items="trustItems" />

      <!-- ════ Services ════ -->
      <ServicesSection :services="services" :service-items="serviceItems" />

      <!-- ════ Comment ça se passe — les étapes ════ -->
      <StepsSection :steps="steps" :step-items="stepItems" />

      <!-- ════ Réalisations / galerie de chantiers ════ -->
      <GallerySection :gallery="gallery" :gallery-items="galleryItems" />

      <!-- ════ Avant / après ════ -->
      <BeforeAfterSection v-if="beforeAfter.before_image && beforeAfter.after_image" :before-after="beforeAfter" />

      <!-- ════ Histoire de l'artisan ════ -->
      <StorySection
        :story="story"
        :story-paragraphs="storyParagraphs"
        :story-values="storyValues"
        :story-stats="storyStats"
        :business-name="businessName"
      />

      <!-- ════ Témoignages ════ -->
      <ReviewsSection v-if="testimonialItems.length" :testimonials="testimonials" :testimonial-items="testimonialItems" />

      <!-- ════ FAQ ════ -->
      <FaqSection :faq="faq" :faq-items="faqItems" />

      <!-- ════ Bandeau urgence fort ════ -->
      <UrgentSection :urgency="urgency" :phone="phone" :phone-href="phoneHref" />

      <!-- ════ Contact ════ -->
      <ContactSection
        :contact="contact"
        :phone="phone"
        :phone-href="phoneHref"
        :email="email"
        :city="city"
        :business-name="businessName"
      />
    </main>

    <footer class="foot">
      <div class="foot-inner">
        <div class="foot-brand">
          <span class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24"><path class="brand-drop" d="M12 3c3 4 5 6.5 5 9a5 5 0 0 1-10 0c0-2.5 2-5 5-9Z" /></svg>
          </span>
          <span>{{ businessName }}</span>
        </div>
        <p class="foot-meta">
          <template v-if="city">{{ city }} · </template>Artisan plombier · Devis gratuit · Urgences 24 h/24
        </p>
        <p class="foot-credit">© {{ year }} {{ businessName }} — Propulsé par DevLeadHunter</p>
      </div>
    </footer>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import { defaultTheme } from './types'
import type { Theme } from './types'
import { icon } from './utils'
import HeroSection from './sections/HeroSection.vue'
import StatsSection from './sections/StatsSection.vue'
import ServicesSection from './sections/ServicesSection.vue'
import StepsSection from './sections/StepsSection.vue'
import GallerySection from './sections/GallerySection.vue'
import BeforeAfterSection from './sections/BeforeAfterSection.vue'
import StorySection from './sections/StorySection.vue'
import ReviewsSection from './sections/ReviewsSection.vue'
import FaqSection from './sections/FaqSection.vue'
import UrgentSection from './sections/UrgentSection.vue'
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
  '--brand': theme.value.primary,
  '--ink': theme.value.secondary,
  '--signal': theme.value.accent,
}))

const blocks: ComputedRef<Block[]> = computed((): Block[] => {
  const body = props.content.body
  return Array.isArray(body) ? (body as Block[]) : []
})
const findBlock = (component: string): Block =>
  blocks.value.find((b: Block): boolean => b.component === component) ?? {}

const hero = computed(() => findBlock('hero'))
const trust = computed(() => findBlock('trust'))
const services = computed(() => findBlock('services'))
const steps = computed(() => findBlock('steps'))
const gallery = computed(() => findBlock('gallery'))
const beforeAfter = computed(() => findBlock('before_after'))
const story = computed(() => findBlock('story'))
const testimonials = computed(() => findBlock('testimonials'))
const faq = computed(() => findBlock('faq'))
const urgency = computed(() => findBlock('urgency'))
const contact = computed(() => findBlock('contact'))

const phone = computed((): string => String(hero.value.phone || contact.value.phone || urgency.value.phone || ''))
const phoneHref = computed((): string => phone.value.replace(/[^\d+]/g, ''))
const city = computed((): string => String(contact.value.city || hero.value.city || ''))
const email = computed((): string => String(contact.value.email || ''))
const year = new Date().getFullYear()

function asArray<T>(v: unknown): T[] {
  return Array.isArray(v) ? (v as T[]) : []
}

const trustItems = computed(() => asArray<{ value?: string; label?: string }>(trust.value.items))
const serviceItems = computed(() =>
  asArray<{ label?: string; description?: string; icon?: string }>(services.value.items),
)
const stepItems = computed(() => asArray<{ title?: string; description?: string; icon?: string }>(steps.value.items))
const galleryItems = computed(() => asArray<{ image?: string; caption?: string; location?: string }>(gallery.value.items))
const storyParagraphs = computed(() => asArray<string>(story.value.paragraphs))
const storyValues = computed(() =>
  asArray<{ label?: string; description?: string; icon?: string }>(story.value.values),
)
const storyStats = computed(() => asArray<{ value?: string; label?: string }>(story.value.stats))
const testimonialItems = computed(() =>
  asArray<{ quote?: string; author?: string; location?: string; rating?: number }>(testimonials.value.items),
)
const faqItems = computed(() => asArray<{ question?: string; answer?: string }>(faq.value.items))

const heroPoints = computed((): string[] => {
  const p = asArray<string>(hero.value.points)
  return p.length ? p : ['Devis gratuit', 'Intervention rapide', 'Travail garanti']
})
const heroChip = computed(() => {
  const first = trustItems.value[0]
  return { value: first?.value || '4,9/5', label: first?.label || 'Avis Google' }
})
const marqueeWords = computed((): string[] => {
  const fromServices = serviceItems.value.map((s) => s.label || '').filter(Boolean)
  return fromServices.length
    ? fromServices
    : ['Dépannage', 'Recherche de fuite', 'Rénovation salle de bain', 'Chauffe-eau', 'Débouchage']
})

/* ── Motion : reveals (IntersectionObserver, robuste) + GSAP pour parallax ── */
const root = ref<HTMLElement | null>(null)
let cleanup: Array<() => void> = []

onMounted(async (): Promise<void> => {
  if (!import.meta.client) return
  const el = root.value
  if (!el) return

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const targets = Array.from(el.querySelectorAll<HTMLElement>('[data-reveal]'))

  if (reduce || !('IntersectionObserver' in window)) {
    targets.forEach((t) => t.classList.add('is-in'))
    return
  }

  const io = new IntersectionObserver(
    (entries, obs): void => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-in')
          obs.unobserve(entry.target)
        }
      }
    },
    { threshold: 0.16, rootMargin: '0px 0px -8% 0px' },
  )
  targets.forEach((t) => io.observe(t))
  cleanup.push(() => io.disconnect())

  // GSAP : parallax hero.
  try {
    const gsapMod = await import('gsap')
    const stMod = await import('gsap/ScrollTrigger')
    const gsap = gsapMod.gsap ?? gsapMod.default
    const ScrollTrigger = stMod.ScrollTrigger ?? stMod.default
    gsap.registerPlugin(ScrollTrigger)

    const heroImg = el.querySelector<HTMLElement>('[data-parallax]')
    if (heroImg) {
      gsap.fromTo(
        heroImg,
        { yPercent: -6 },
        {
          yPercent: 6,
          ease: 'none',
          scrollTrigger: { trigger: heroImg, start: 'top bottom', end: 'bottom top', scrub: true },
        },
      )
    }
    cleanup.push(() => ScrollTrigger.getAll().forEach((t: { kill: () => void }) => t.kill()))
  } catch {
    /* GSAP indisponible : les reveals CSS/IO suffisent. */
  }
})

onBeforeUnmount((): void => {
  cleanup.forEach((fn) => fn())
  cleanup = []
})
</script>

<style scoped>
/* ════════════ Tokens & fondations ════════════ */
.sig {
  --paper: #f6f3ee;
  --paper-2: #efe9e0;
  --mist: #e7eeec;
  --brand-soft: color-mix(in srgb, var(--brand) 12%, var(--paper));
  --brand-deep: color-mix(in srgb, var(--brand) 78%, #000);
  --hair: color-mix(in srgb, var(--ink) 14%, transparent);
  --ink-soft: color-mix(in srgb, var(--ink) 62%, var(--paper));

  background: var(--paper);
  color: var(--ink);
  font-family: 'Archivo', system-ui, sans-serif;
  font-size: 16px;
  line-height: 1.6;
  position: relative;
  overflow-x: clip;
}
.sig :deep(svg) {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.sig :deep(.star) {
  fill: color-mix(in srgb, var(--ink) 18%, transparent);
  stroke: none;
}
.sig :deep(.star-on) {
  fill: var(--signal);
}
.sig :deep(.brand-drop) {
  fill: currentColor;
  stroke: none;
}

.sig :deep(.btn) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  font-family: 'Archivo', sans-serif;
  font-weight: 650;
  font-size: 0.96rem;
  letter-spacing: 0.005em;
  padding: 0.9rem 1.5rem;
  border-radius: 999px;
  cursor: pointer;
  border: 0;
  text-align: center;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease, color 0.18s ease;
}
.sig :deep(.btn .ico) {
  width: 1.05rem;
  height: 1.05rem;
}
.sig :deep(.btn-signal) {
  background: var(--signal);
  color: #fff;
  box-shadow: 0 8px 22px -8px color-mix(in srgb, var(--signal) 70%, transparent);
}
.sig :deep(.btn-signal:hover) {
  transform: translateY(-2px);
  box-shadow: 0 14px 30px -10px color-mix(in srgb, var(--signal) 75%, transparent);
}
.sig :deep(.btn-ghost) {
  background: transparent;
  color: var(--ink);
  border: 1.5px solid color-mix(in srgb, var(--ink) 26%, transparent);
}
.sig :deep(.btn-ghost:hover) {
  border-color: var(--ink);
  background: var(--ink);
  color: var(--paper);
  transform: translateY(-2px);
}

/* ════════════ Bandeau urgence ════════════ */
.alertbar {
  background: var(--ink);
  color: var(--paper);
  font-size: 0.82rem;
}
.alertbar-inner {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0.55rem 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.alertbar-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--signal);
  box-shadow: 0 0 0 0 color-mix(in srgb, var(--signal) 70%, transparent);
  animation: pulse 2s infinite;
  flex: none;
}
@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--signal) 60%, transparent);
  }
  70% {
    box-shadow: 0 0 0 7px transparent;
  }
  100% {
    box-shadow: 0 0 0 0 transparent;
  }
}
.alertbar-text {
  color: color-mix(in srgb, var(--paper) 82%, transparent);
}
.alertbar-phone {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 700;
  color: #fff;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.alertbar-phone .ico {
  width: 0.95rem;
  height: 0.95rem;
  color: var(--signal);
}
.alertbar-phone:hover {
  color: var(--signal);
}

/* ════════════ Header ════════════ */
.nav {
  position: sticky;
  top: 0;
  z-index: 50;
  background: color-mix(in srgb, var(--paper) 85%, transparent);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--hair);
}
.nav-inner {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0.85rem 1.5rem;
  display: flex;
  align-items: center;
  gap: 1.5rem;
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  font-family: 'Bricolage Grotesque', 'Archivo', sans-serif;
  font-weight: 700;
  font-size: 1.18rem;
  letter-spacing: -0.02em;
  color: var(--ink);
}
.brand-mark {
  width: 2rem;
  height: 2rem;
  border-radius: 9px;
  background: var(--brand);
  color: #fff;
  display: grid;
  place-items: center;
  flex: none;
}
.brand-mark svg {
  width: 1.15rem;
  height: 1.15rem;
}
.nav-links {
  margin-left: auto;
  display: flex;
  gap: 1.6rem;
}
.nav-links a {
  font-size: 0.9rem;
  font-weight: 550;
  color: var(--ink-soft);
  position: relative;
  transition: color 0.18s ease;
}
.nav-links a::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: -4px;
  width: 0;
  height: 2px;
  background: var(--signal);
  transition: width 0.22s ease;
}
.nav-links a:hover {
  color: var(--ink);
}
.nav-links a:hover::after {
  width: 100%;
}
.nav-cta {
  font-size: 0.88rem;
  font-weight: 650;
  padding: 0.55rem 1.1rem;
  border-radius: 999px;
  background: var(--ink);
  color: var(--paper);
  transition: background 0.18s ease, transform 0.18s ease;
}
.nav-cta:hover {
  background: var(--brand);
  transform: translateY(-1px);
}

/* ════════════ Sections génériques ════════════ */
.sig :deep(.section-head) {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 1.5rem;
}
.sig :deep(.kicker) {
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: var(--signal);
  margin-bottom: 0.9rem;
}
.sig :deep(.kicker-light) {
  color: color-mix(in srgb, var(--signal) 88%, #fff);
}
.sig :deep(.section-title) {
  font-family: 'Bricolage Grotesque', 'Archivo', sans-serif;
  font-weight: 700;
  font-size: clamp(2rem, 4vw, 3.1rem);
  line-height: 1.04;
  letter-spacing: -0.03em;
  max-width: 20ch;
}
.sig :deep(.section-title-light) {
  color: var(--paper);
}
.sig :deep(.section-lede) {
  margin-top: 1rem;
  color: var(--ink-soft);
  max-width: 50ch;
  font-size: 1.05rem;
}
.sig :deep(.section-lede-light) {
  color: color-mix(in srgb, var(--paper) 72%, transparent);
}

/* ════════════ Footer ════════════ */
.foot {
  background: var(--ink);
  color: color-mix(in srgb, var(--paper) 70%, transparent);
}
.foot-inner {
  max-width: 1240px;
  margin: 0 auto;
  padding: 2.5rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  align-items: center;
  text-align: center;
}
.foot-brand {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700;
  font-size: 1.2rem;
  color: var(--paper);
}
.foot-meta {
  font-size: 0.92rem;
}
.foot-credit {
  font-size: 0.78rem;
  color: color-mix(in srgb, var(--paper) 45%, transparent);
}

/* ════════════ Reveals ════════════ */
.sig :deep(.reveal) {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.7s cubic-bezier(0.22, 1, 0.36, 1) var(--d, 0ms),
    transform 0.7s cubic-bezier(0.22, 1, 0.36, 1) var(--d, 0ms);
  will-change: opacity, transform;
}
.sig :deep(.reveal.is-in) {
  opacity: 1;
  transform: none;
}

/* ════════════ Responsive ════════════ */
@media (max-width: 680px) {
  .nav-links {
    display: none;
  }
  .alertbar-text {
    display: none;
  }
  .alertbar-phone {
    margin-left: 0;
  }
  .alertbar-inner {
    justify-content: space-between;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sig :deep(.reveal) {
    opacity: 1;
    transform: none;
    transition: none;
  }
  .alertbar-pulse {
    animation: none;
  }
}
</style>
