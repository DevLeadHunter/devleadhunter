<template>
  <div ref="rootRef" class="lumen" :class="{ 'lumen--boot': !isBootDone, 'lumen--js': isClientReady }" :style="themeVars">
    <!-- Nav -->
    <nav class="lumen-nav" data-lumen-boot="8" aria-label="Navigation principale">
      <div class="lumen-container lumen-nav__inner">
        <a href="#" class="lumen-nav__brand">
          <span class="lumen-nav__brand-mark" aria-hidden="true">
            <LumenIcon name="panne" class="lumen-nav__brand-icon" />
          </span>
          <span class="lumen-nav__brand-name">{{ parsed.hero.title || businessName }}</span>
        </a>

        <ul class="lumen-nav__links">
          <li><a href="#depannage" class="lumen-nav__link">Dépannage</a></li>
          <li><a href="#services" class="lumen-nav__link">Services</a></li>
          <li><a href="#securite" class="lumen-nav__link">Sécurité</a></li>
          <li><a href="#faq" class="lumen-nav__link">FAQ</a></li>
        </ul>

        <div class="lumen-nav__actions">
          <a v-if="parsed.hero.phone" :href="`tel:${parsed.hero.phone}`" class="lumen-nav__phone">
            <LumenIcon name="phone" class="lumen-nav__phone-icon" />
            <span class="lumen-nav__phone-number">{{ parsed.hero.phone }}</span>
          </a>
          <a href="#contact" class="lumen-btn lumen-btn--primary lumen-nav__cta">Devis gratuit</a>
        </div>
      </div>
    </nav>

    <main>
      <HeroSection :hero="parsed.hero" :business-name="businessName" />
      <TrustStripSection :items="parsed.trustItems" />
      <EmergencySection :emergency="parsed.emergency" />
      <ServicesSection :services="parsed.services" />
      <SafetySection :safety="parsed.safety" />
      <GallerySection :gallery="parsed.gallery" />
      <ProcessSection :process="parsed.process" />
      <ReviewsSection :reviews="parsed.reviews" />
      <ZoneSection :zone="parsed.zone" />
      <FaqSection :faq="parsed.faq" />
      <ContactSection :contact="parsed.contact" />
    </main>

    <footer class="lumen-footer">
      <div class="lumen-container lumen-footer__inner">
        <p class="lumen-footer__brand">{{ parsed.hero.title || businessName }}</p>
        <p class="lumen-footer__meta">
          <template v-if="parsed.contact.city">{{ parsed.contact.city }} · </template>
          <template v-if="parsed.contact.phone">{{ parsed.contact.phone }} · </template>
          © {{ currentYear }} — Tous droits réservés
        </p>
      </div>
    </footer>

    <!-- Filament de progression (desktop) -->
    <div class="lumen__filament" aria-hidden="true">
      <div ref="filamentFillRef" class="lumen__filament-fill"></div>
    </div>

    <!-- Grain -->
    <div class="lumen__grain" aria-hidden="true"></div>
  </div>
</template>

<script lang="ts" setup>
/**
 * Template 'electrician-lumen' — direction artistique « Nuit électrique ».
 * La page « s'allume » au chargement (timeline GSAP : flicker puis reveals
 * échelonnés), un filament lumineux se charge au fil du scroll, et chaque
 * section se révèle à l'entrée à l'écran (IntersectionObserver + CSS).
 * Tout est désactivé quand l'utilisateur préfère réduire les animations.
 */
import type { ComputedRef, Ref } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import HeroSection from './sections/HeroSection.vue'
import TrustStripSection from './sections/TrustStripSection.vue'
import EmergencySection from './sections/EmergencySection.vue'
import ServicesSection from './sections/ServicesSection.vue'
import SafetySection from './sections/SafetySection.vue'
import GallerySection from './sections/GallerySection.vue'
import ProcessSection from './sections/ProcessSection.vue'
import ReviewsSection from './sections/ReviewsSection.vue'
import ZoneSection from './sections/ZoneSection.vue'
import FaqSection from './sections/FaqSection.vue'
import ContactSection from './sections/ContactSection.vue'
import LumenIcon from './sections/LumenIcon.vue'
import { parseLumenContent } from './types'
import type { LumenPageContent } from './types'

const props = defineProps<{
  content: Record<string, unknown>
  businessName: string
}>()

const rootRef: Ref<HTMLElement | null> = ref(null)
const filamentFillRef: Ref<HTMLElement | null> = ref(null)
const isBootDone: Ref<boolean> = ref(false)
const isClientReady: Ref<boolean> = ref(false)

const parsed: ComputedRef<LumenPageContent> = computed((): LumenPageContent => parseLumenContent(props.content))

const currentYear: number = new Date().getFullYear()

const themeVars: ComputedRef<Record<string, string>> = computed(
  (): Record<string, string> => ({
    '--lumen-yellow': parsed.value.theme.primary,
    '--lumen-night': parsed.value.theme.secondary,
    '--lumen-amber': parsed.value.theme.accent,
  }),
)

let revealObserver: IntersectionObserver | null = null
let bootTimeline: gsap.core.Timeline | null = null
let filamentTrigger: ScrollTrigger | null = null
let bootFallbackTimer: number | null = null

/**
 * Observe tous les éléments annotés `data-lumen-reveal` pas encore révélés
 * (idempotent : ré-appelable quand le contenu change via le bridge Storyblok).
 * @returns void
 */
function observeRevealTargets(): void {
  if (!revealObserver || !rootRef.value) {
    return
  }
  rootRef.value.querySelectorAll<HTMLElement>('[data-lumen-reveal]:not(.is-lit)').forEach((element: HTMLElement): void => {
    revealObserver?.observe(element)
  })
}

/**
 * Joue la séquence « allumage » du hero : flicker de la lueur et du titre
 * (comme un tube qu'on rallume), puis reveals échelonnés du reste.
 * @param heroElements Éléments `data-lumen-boot` triés par ordre d'allumage.
 * @returns void
 */
function playPowerOn(heroElements: HTMLElement[]): void {
  const glow: HTMLElement | null = rootRef.value?.querySelector('[data-lumen-glow]') ?? null
  const title: HTMLElement | undefined = heroElements.find(
    (element: HTMLElement): boolean => element.dataset.lumenBoot === '2',
  )
  const others: HTMLElement[] = heroElements.filter((element: HTMLElement): boolean => element !== title)

  bootTimeline = gsap.timeline({ defaults: { ease: 'power3.out' } })
  bootTimeline.set(heroElements, { autoAlpha: 0, y: 16 })
  if (glow) {
    bootTimeline.set(glow, { autoAlpha: 0 })
  }
  // Les styles inline pilotent désormais l'opacité : on retire l'état CSS de boot.
  bootTimeline.call((): void => {
    isBootDone.value = true
  })
  if (glow) {
    bootTimeline.to(glow, { keyframes: { autoAlpha: [0, 0.7, 0.2, 1] }, duration: 0.5, ease: 'none' }, 0.05)
  }
  if (title) {
    bootTimeline.to(title, { keyframes: { autoAlpha: [0, 0.6, 0.15, 0.85, 0.4, 1] }, y: 0, duration: 0.55, ease: 'none' }, 0.1)
  }
  bootTimeline.to(others, { autoAlpha: 1, y: 0, duration: 0.55, stagger: 0.07 }, 0.38)
}

onMounted((): void => {
  isClientReady.value = true
  const reducedMotion: boolean = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const heroElements: HTMLElement[] = Array.from(
    rootRef.value?.querySelectorAll<HTMLElement>('[data-lumen-boot]') ?? [],
  ).sort((a: HTMLElement, b: HTMLElement): number => Number(a.dataset.lumenBoot) - Number(b.dataset.lumenBoot))

  if (reducedMotion) {
    isBootDone.value = true
    return
  }

  // Filet de sécurité : si la timeline échoue, tout redevient visible.
  bootFallbackTimer = window.setTimeout((): void => {
    if (!isBootDone.value) {
      isBootDone.value = true
      gsap.set(heroElements, { autoAlpha: 1, y: 0 })
    }
  }, 2500)

  playPowerOn(heroElements)

  // Reveals au scroll.
  revealObserver = new IntersectionObserver(
    (entries: IntersectionObserverEntry[]): void => {
      entries.forEach((entry: IntersectionObserverEntry): void => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-lit')
          revealObserver?.unobserve(entry.target)
        }
      })
    },
    { threshold: 0.12, rootMargin: '0px 0px -8% 0px' },
  )
  observeRevealTargets()

  // Filament de progression relié au scroll de la page.
  gsap.registerPlugin(ScrollTrigger)
  if (filamentFillRef.value && rootRef.value) {
    filamentTrigger = ScrollTrigger.create({
      trigger: rootRef.value,
      start: 'top top',
      end: 'bottom bottom',
      scrub: 0.4,
      animation: gsap.fromTo(filamentFillRef.value, { scaleY: 0 }, { scaleY: 1, ease: 'none' }),
    })
  }
})

// Le bridge Storyblok remplace le contenu à la volée : on ré-observe les
// nouveaux éléments à révéler (galerie/avis qui apparaissent, etc.).
watch(parsed, async (): Promise<void> => {
  await nextTick()
  observeRevealTargets()
})

onUnmounted((): void => {
  revealObserver?.disconnect()
  bootTimeline?.kill()
  filamentTrigger?.kill()
  if (bootFallbackTimer !== null) {
    window.clearTimeout(bootFallbackTimer)
  }
})
</script>

<!--
  Styles volontairement non scopés : c'est le mini design-system de la template,
  partagé par toutes ses sections. Toutes les classes sont préfixées `lumen-`
  (et les variables `-lumen-`) — aucune fuite possible vers les autres templates.
-->
<style>
.lumen {
  /* Palette dérivée du thème client (primary/secondary/accent éditables). */
  --lumen-panel: color-mix(in srgb, var(--lumen-night), white 4%);
  --lumen-raised: color-mix(in srgb, var(--lumen-night), white 8%);
  --lumen-line: color-mix(in srgb, white 10%, transparent);
  --lumen-text: #e9eef6;
  --lumen-muted: #93a0b8;
  --lumen-nav-height: 4.3rem;
  --lumen-font-display: 'Chakra Petch', 'Archivo', sans-serif;
  --lumen-font-mono: 'IBM Plex Mono', ui-monospace, monospace;
  --lumen-font-body: 'Archivo', sans-serif;

  position: relative;
  background: var(--lumen-night);
  color: var(--lumen-text);
  font-family: var(--lumen-font-body);
  overflow-x: clip;
}

.lumen [id] {
  scroll-margin-top: calc(var(--lumen-nav-height) + 1rem);
}

.lumen ::selection {
  background: var(--lumen-yellow);
  color: var(--lumen-night);
}

.lumen :focus-visible {
  outline: 2px solid var(--lumen-yellow);
  outline-offset: 2px;
}

/* ---- Layout ---- */

.lumen-container {
  max-width: 74rem;
  margin-inline: auto;
  padding-inline: clamp(1.25rem, 4vw, 2.5rem);
}

.lumen-section {
  padding-top: 6rem;
}

.lumen-section__head {
  max-width: 46rem;
}

.lumen-section__subheading {
  margin-top: 0.95rem;
  line-height: 1.65;
  color: var(--lumen-muted);
}

/* ---- Typo partagée ---- */

.lumen-heading {
  margin-top: 1rem;
  font-family: var(--lumen-font-display);
  font-weight: 700;
  font-size: clamp(1.7rem, 3.6vw, 2.5rem);
  line-height: 1.08;
  text-transform: uppercase;
  letter-spacing: 0.005em;
  color: var(--lumen-text);
  text-wrap: balance;
}

.lumen-kicker {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-family: var(--lumen-font-mono);
  font-size: 0.74rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--lumen-yellow);
}

.lumen-kicker::before {
  content: '';
  width: 7px;
  height: 7px;
  flex: none;
  background: currentcolor;
  box-shadow: 0 0 10px 1px color-mix(in srgb, currentcolor 75%, transparent);
}

.lumen-kicker--amber {
  color: var(--lumen-amber);
}

/* ---- Boutons ---- */

.lumen-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  padding: 0.85rem 1.5rem;
  font-family: var(--lumen-font-display);
  font-weight: 600;
  font-size: 0.88rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  text-decoration: none;
  cursor: pointer;
  clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
  transition:
    filter 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease,
    transform 0.2s ease;
}

.lumen-btn__icon {
  width: 15px;
  height: 15px;
}

.lumen-btn--primary {
  background: var(--lumen-yellow);
  color: var(--lumen-night);
  box-shadow: 0 10px 34px -12px color-mix(in srgb, var(--lumen-yellow) 65%, transparent);
}

.lumen-btn--primary:hover {
  filter: brightness(1.07);
  transform: translateY(-1px);
  box-shadow: 0 14px 40px -12px color-mix(in srgb, var(--lumen-yellow) 80%, transparent);
}

.lumen-btn--ghost {
  border: 1px solid color-mix(in srgb, white 24%, transparent);
  color: var(--lumen-text);
  background: color-mix(in srgb, white 3%, transparent);
}

.lumen-btn--ghost:hover {
  border-color: color-mix(in srgb, var(--lumen-yellow) 60%, transparent);
  color: var(--lumen-yellow);
}

/* ---- Nav ---- */

.lumen-nav {
  position: fixed;
  inset-inline: 0;
  top: 0;
  z-index: 50;
  height: var(--lumen-nav-height);
  background: color-mix(in srgb, var(--lumen-night) 82%, transparent);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--lumen-line);
}

.lumen-nav__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  height: 100%;
}

.lumen-nav__brand {
  display: inline-flex;
  align-items: center;
  gap: 0.7rem;
  text-decoration: none;
  min-width: 0;
}

.lumen-nav__brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex: none;
  background: var(--lumen-yellow);
  clip-path: polygon(7px 0, 100% 0, 100% calc(100% - 7px), calc(100% - 7px) 100%, 0 100%, 0 7px);
}

.lumen-nav__brand-icon {
  width: 17px;
  height: 17px;
  color: var(--lumen-night);
}

.lumen-nav__brand-name {
  font-family: var(--lumen-font-display);
  font-weight: 600;
  font-size: 0.95rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--lumen-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 40vw;
}

.lumen-nav__links {
  display: none;
  align-items: center;
  gap: 1.7rem;
  list-style: none;
  margin: 0;
  padding: 0;
}

@media (min-width: 1024px) {
  .lumen-nav__links {
    display: flex;
  }
}

.lumen-nav__link {
  font-size: 0.86rem;
  color: var(--lumen-muted);
  text-decoration: none;
  transition: color 0.2s ease;
}

.lumen-nav__link:hover {
  color: var(--lumen-yellow);
}

.lumen-nav__actions {
  display: flex;
  align-items: center;
  gap: 0.9rem;
}

.lumen-nav__phone {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--lumen-text);
  text-decoration: none;
  transition: color 0.2s ease;
}

.lumen-nav__phone:hover {
  color: var(--lumen-yellow);
}

.lumen-nav__phone-icon {
  width: 16px;
  height: 16px;
  color: var(--lumen-yellow);
}

.lumen-nav__phone-number {
  display: none;
  font-family: var(--lumen-font-mono);
  font-size: 0.86rem;
}

@media (min-width: 768px) {
  .lumen-nav__phone-number {
    display: inline;
  }
}

.lumen-nav__cta {
  padding: 0.6rem 1.05rem;
  font-size: 0.78rem;
}

/* ---- Footer ---- */

.lumen-footer {
  border-top: 1px solid var(--lumen-line);
  padding: 2.2rem 0 2.6rem;
}

.lumen-footer__inner {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.8rem 2rem;
}

.lumen-footer__brand {
  font-family: var(--lumen-font-display);
  font-weight: 600;
  font-size: 0.95rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--lumen-text);
}

.lumen-footer__meta {
  font-family: var(--lumen-font-mono);
  font-size: 0.74rem;
  letter-spacing: 0.06em;
  color: var(--lumen-muted);
}

/* ---- Allumage & reveals ---- */

.lumen--boot [data-lumen-boot],
.lumen--boot [data-lumen-glow] {
  opacity: 0;
  visibility: hidden;
}

.lumen--js [data-lumen-reveal] {
  opacity: 0;
  transform: translateY(26px);
  transition:
    opacity 0.7s ease,
    transform 0.7s cubic-bezier(0.22, 1, 0.36, 1);
  transition-delay: var(--lumen-reveal-delay, 0ms);
}

.lumen--js [data-lumen-reveal].is-lit {
  opacity: 1;
  transform: none;
}

/* ---- Filament de scroll (desktop large) ---- */

.lumen__filament {
  display: none;
  position: fixed;
  left: 20px;
  top: 16vh;
  bottom: 16vh;
  width: 2px;
  background: color-mix(in srgb, white 7%, transparent);
  z-index: 40;
  pointer-events: none;
}

@media (min-width: 1280px) {
  .lumen__filament {
    display: block;
  }
}

.lumen__filament-fill {
  width: 100%;
  height: 100%;
  transform: scaleY(0);
  transform-origin: top;
  background: linear-gradient(180deg, var(--lumen-yellow), var(--lumen-amber));
  box-shadow: 0 0 12px color-mix(in srgb, var(--lumen-yellow) 55%, transparent);
}

/* ---- Grain ---- */

.lumen__grain {
  position: fixed;
  inset: 0;
  z-index: 45;
  pointer-events: none;
  opacity: 0.05;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

/* ---- Reduced motion : tout visible, rien n'anime ---- */

@media (prefers-reduced-motion: reduce) {
  .lumen--boot [data-lumen-boot],
  .lumen--boot [data-lumen-glow] {
    opacity: 1;
    visibility: visible;
  }

  .lumen--js [data-lumen-reveal] {
    opacity: 1;
    transform: none;
    transition: none;
  }

  .lumen__filament {
    display: none;
  }
}
</style>
