<template>
  <div ref="rootRef" class="cuivre" :class="{ 'cuivre--boot': !isIntroReady, 'cuivre--ready': isIntroReady, 'cuivre--js': isClientReady }" :style="themeVars">
    <!-- Barre d'appel épinglée (apparaît une fois la manchette passée) -->
    <div class="cuivre-bar" :class="{ 'is-pinned': isBarPinned }" aria-hidden="false">
      <div class="cuivre-container cuivre-bar__inner">
        <span class="cuivre-bar__name">{{ parsed.hero.title || businessName }}</span>
        <div class="cuivre-bar__actions">
          <a v-if="parsed.hero.phone" :href="`tel:${parsed.hero.phone}`" class="cuivre-bar__phone">
            <CuivreGlyph name="phone" class="cuivre-bar__phone-icon" />
            <span class="cuivre-bar__phone-number">{{ parsed.hero.phone }}</span>
          </a>
          <a href="#contact" class="cuivre-btn cuivre-btn--blue cuivre-bar__cta">Devis gratuit</a>
        </div>
      </div>
    </div>

    <main>
      <div ref="heroWrapRef">
        <HeroSection :hero="parsed.hero" :business-name="businessName" />
      </div>
      <TrustBandSection :items="parsed.trustItems" />
      <EmergencySection :emergency="parsed.emergency" />
      <ServicesSection :services="parsed.services" />
      <CraftSection :craft="parsed.craft" />
      <AboutSection :about="parsed.about" />
      <GallerySection :gallery="parsed.gallery" />
      <ProcessSection :process="parsed.process" />
      <ReviewsSection :reviews="parsed.reviews" />
      <BrandsSection :brands="parsed.brands" />
      <ZoneSection :zone="parsed.zone" />
      <FaqSection :faq="parsed.faq" />
      <ContactSection :contact="parsed.contact" />
    </main>

    <footer class="cuivre-footer">
      <div class="cuivre-container cuivre-footer__inner">
        <p class="cuivre-footer__brand">{{ parsed.hero.title || businessName }}</p>
        <p class="cuivre-footer__meta">
          <template v-if="parsed.contact.city">{{ parsed.contact.city }} · </template>
          <template v-if="parsed.contact.phone">{{ parsed.contact.phone }} · </template>
          © {{ currentYear }} — Tous droits réservés
        </p>
      </div>
    </footer>
  </div>
</template>

<script lang="ts" setup>
/**
 * Template 'plumber-cuivre' (« Plombier Source ») — direction artistique « Source ».
 * Vitrine claire et fraîche : fond blanc teinté d'eau, encre marine, bleu eau et
 * turquoise, typo display robuste et boutons pilule. Intro orchestrée en CSS pur,
 * reveals doux au scroll via IntersectionObserver, barre d'appel épinglée après
 * la manchette. Tout est désactivé quand l'utilisateur réduit les animations.
 */
import type { ComputedRef, Ref } from 'vue'
import HeroSection from './sections/HeroSection.vue'
import TrustBandSection from './sections/TrustBandSection.vue'
import EmergencySection from './sections/EmergencySection.vue'
import ServicesSection from './sections/ServicesSection.vue'
import CraftSection from './sections/CraftSection.vue'
import AboutSection from './sections/AboutSection.vue'
import GallerySection from './sections/GallerySection.vue'
import ProcessSection from './sections/ProcessSection.vue'
import ReviewsSection from './sections/ReviewsSection.vue'
import BrandsSection from './sections/BrandsSection.vue'
import ZoneSection from './sections/ZoneSection.vue'
import FaqSection from './sections/FaqSection.vue'
import ContactSection from './sections/ContactSection.vue'
import CuivreGlyph from './sections/CuivreGlyph.vue'
import { parseCuivreContent } from './types'
import type { CuivrePageContent } from './types'

const props = defineProps<{
  content: Record<string, unknown>
  businessName: string
}>()

const rootRef: Ref<HTMLElement | null> = ref(null)
const heroWrapRef: Ref<HTMLElement | null> = ref(null)
const isIntroReady: Ref<boolean> = ref(false)
const isClientReady: Ref<boolean> = ref(false)
const isBarPinned: Ref<boolean> = ref(false)

const parsed: ComputedRef<CuivrePageContent> = computed((): CuivrePageContent => parseCuivreContent(props.content))

const currentYear: number = new Date().getFullYear()

const themeVars: ComputedRef<Record<string, string>> = computed(
  (): Record<string, string> => ({
    '--cuivre-blue': parsed.value.theme.primary,
    '--cuivre-ink': parsed.value.theme.secondary,
    '--cuivre-aqua': parsed.value.theme.accent,
  }),
)

let revealObserver: IntersectionObserver | null = null
let barObserver: IntersectionObserver | null = null

/**
 * Observe tous les éléments annotés `data-cuivre-reveal` pas encore révélés
 * (idempotent : ré-appelable quand le contenu change via le bridge Storyblok).
 * @returns void
 */
function observeRevealTargets(): void {
  if (!revealObserver || !rootRef.value) {
    return
  }
  rootRef.value.querySelectorAll<HTMLElement>('[data-cuivre-reveal]:not(.is-inked)').forEach((element: HTMLElement): void => {
    revealObserver?.observe(element)
  })
}

onMounted((): void => {
  isClientReady.value = true
  const reducedMotion: boolean = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  if (reducedMotion) {
    isIntroReady.value = true
  } else {
    // Double rAF : l'état « boot » est peint, puis la transition d'intro se joue.
    window.requestAnimationFrame((): void => {
      window.requestAnimationFrame((): void => {
        isIntroReady.value = true
      })
    })
  }

  // Reveals au scroll.
  revealObserver = new IntersectionObserver(
    (entries: IntersectionObserverEntry[]): void => {
      entries.forEach((entry: IntersectionObserverEntry): void => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-inked')
          revealObserver?.unobserve(entry.target)
        }
      })
    },
    { threshold: 0.12, rootMargin: '0px 0px -7% 0px' },
  )
  observeRevealTargets()

  // Barre d'appel : épinglée dès que le hero (manchette comprise) est sorti de l'écran.
  barObserver = new IntersectionObserver(
    (entries: IntersectionObserverEntry[]): void => {
      entries.forEach((entry: IntersectionObserverEntry): void => {
        isBarPinned.value = !entry.isIntersecting
      })
    },
    { rootMargin: '-70px 0px 0px 0px', threshold: 0 },
  )
  if (heroWrapRef.value) {
    barObserver.observe(heroWrapRef.value)
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
  barObserver?.disconnect()
})
</script>

<!--
  Styles volontairement non scopés : c'est le mini design-system de la template,
  partagé par toutes ses sections. Toutes les classes sont préfixées `cuivre-`
  (codename interne de la template) — aucune fuite possible vers les autres templates.
-->
<style>
.cuivre {
  /* Palette dérivée du thème client (primary=bleu eau, secondary=encre marine, accent=turquoise). */
  --cuivre-bg: color-mix(in srgb, #f7fbfd 97%, var(--cuivre-blue));
  --cuivre-card: #ffffff;
  --cuivre-tint: color-mix(in srgb, var(--cuivre-blue) 6%, white);
  --cuivre-rule: color-mix(in srgb, var(--cuivre-ink) 13%, transparent);
  --cuivre-muted: color-mix(in srgb, var(--cuivre-ink) 68%, white);
  --cuivre-blue-light: color-mix(in srgb, var(--cuivre-aqua) 70%, white);
  --cuivre-font-display: 'Bricolage Grotesque', 'Archivo', sans-serif;
  --cuivre-font-sans: 'Archivo', sans-serif;

  position: relative;
  background: var(--cuivre-bg);
  color: var(--cuivre-ink);
  font-family: var(--cuivre-font-sans);
  overflow-x: clip;
}

.cuivre [id] {
  scroll-margin-top: 4.6rem;
}

.cuivre ::selection {
  background: var(--cuivre-blue);
  color: #ffffff;
}

.cuivre :focus-visible {
  outline: 2px solid var(--cuivre-blue);
  outline-offset: 2px;
}

/* ---- Layout ---- */

.cuivre-container {
  max-width: 72rem;
  margin-inline: auto;
  padding-inline: clamp(1.25rem, 4vw, 2.5rem);
}

.cuivre-section {
  padding-top: 5.5rem;
}

.cuivre-section__head {
  max-width: 46rem;
}

.cuivre-section__subheading {
  margin-top: 0.95rem;
  font-family: var(--cuivre-font-sans);
  line-height: 1.65;
  color: var(--cuivre-muted);
}

/* ---- Typo partagée ---- */

.cuivre-heading {
  margin-top: 0.95rem;
  font-family: var(--cuivre-font-display);
  font-weight: 700;
  font-size: clamp(1.75rem, 3.6vw, 2.55rem);
  line-height: 1.12;
  letter-spacing: -0.01em;
  color: var(--cuivre-ink);
  text-wrap: balance;
}

/* Chip de section : pastille goutte + numéro + libellé */
.cuivre-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.42rem 0.95rem 0.42rem 0.6rem;
  border-radius: 9999px;
  background: color-mix(in srgb, var(--cuivre-aqua) 13%, white);
  border: 1px solid color-mix(in srgb, var(--cuivre-aqua) 35%, transparent);
  font-family: var(--cuivre-font-display);
  font-weight: 700;
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--cuivre-blue);
}

.cuivre-eyebrow::before {
  content: '';
  width: 8px;
  height: 8px;
  flex: none;
  border-radius: 9999px 9999px 9999px 2px;
  transform: rotate(45deg);
  background: var(--cuivre-blue);
}

.cuivre-eyebrow__num {
  font-family: var(--cuivre-font-display);
  font-weight: 600;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  color: color-mix(in srgb, var(--cuivre-blue) 55%, var(--cuivre-muted));
}

/* ---- Boutons (pilules) ---- */

.cuivre-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  padding: 0.85rem 1.65rem;
  border-radius: 9999px;
  font-family: var(--cuivre-font-display);
  font-weight: 700;
  font-size: 0.92rem;
  letter-spacing: 0.005em;
  text-decoration: none;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.cuivre-btn__icon {
  width: 15px;
  height: 15px;
}

.cuivre-btn--blue {
  background: var(--cuivre-blue);
  color: #ffffff;
  box-shadow: 0 12px 28px -14px color-mix(in srgb, var(--cuivre-blue) 85%, transparent);
}

.cuivre-btn--blue:hover {
  background: color-mix(in srgb, var(--cuivre-blue) 86%, var(--cuivre-ink));
  transform: translateY(-1px);
  box-shadow: 0 16px 32px -14px color-mix(in srgb, var(--cuivre-blue) 95%, transparent);
}

.cuivre-btn--ghost {
  border: 1.5px solid color-mix(in srgb, var(--cuivre-ink) 22%, transparent);
  color: var(--cuivre-ink);
  background: var(--cuivre-card);
}

.cuivre-btn--ghost:hover {
  border-color: var(--cuivre-blue);
  color: var(--cuivre-blue);
}

/* ---- Séparateur vague (motif métier) ---- */

.cuivre-wave {
  height: 9px;
  background-color: color-mix(in srgb, var(--cuivre-blue) 55%, transparent);
  mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='36' height='9' viewBox='0 0 36 9'%3E%3Cpath d='M0 6.5C4.5 6.5 4.5 2 9 2s4.5 4.5 9 4.5S22.5 2 27 2s4.5 4.5 9 4.5' fill='none' stroke='black' stroke-width='1.6' stroke-linecap='round'/%3E%3C/svg%3E");
  mask-repeat: repeat-x;
  mask-position: left center;
  -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='36' height='9' viewBox='0 0 36 9'%3E%3Cpath d='M0 6.5C4.5 6.5 4.5 2 9 2s4.5 4.5 9 4.5S22.5 2 27 2s4.5 4.5 9 4.5' fill='none' stroke='black' stroke-width='1.6' stroke-linecap='round'/%3E%3C/svg%3E");
  -webkit-mask-repeat: repeat-x;
  -webkit-mask-position: left center;
}

/* ---- Barre d'appel épinglée ---- */

.cuivre-bar {
  position: fixed;
  inset-inline: 0;
  top: 0;
  z-index: 50;
  background: color-mix(in srgb, var(--cuivre-card) 90%, transparent);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--cuivre-rule);
  transform: translateY(-105%);
  transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}

.cuivre-bar.is-pinned {
  transform: translateY(0);
}

.cuivre-bar__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.4rem;
  height: 3.6rem;
}

.cuivre-bar__name {
  font-family: var(--cuivre-font-display);
  font-weight: 700;
  font-size: 1rem;
  color: var(--cuivre-ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.cuivre-bar__actions {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: none;
}

.cuivre-bar__phone {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-family: var(--cuivre-font-sans);
  font-weight: 600;
  font-size: 0.86rem;
  white-space: nowrap;
  color: var(--cuivre-ink);
  text-decoration: none;
  transition: color 0.2s ease;
}

.cuivre-bar__phone:hover {
  color: var(--cuivre-blue);
}

.cuivre-bar__phone-icon {
  width: 14px;
  height: 14px;
  color: var(--cuivre-blue);
}

.cuivre-bar__phone-number {
  display: none;
}

@media (min-width: 640px) {
  .cuivre-bar__phone-number {
    display: inline;
  }
}

.cuivre-bar__cta {
  padding: 0.52rem 1.1rem;
  font-size: 0.8rem;
}

/* ---- Footer ---- */

.cuivre-footer {
  background: var(--cuivre-ink);
  color: #ffffff;
  padding: 2.2rem 0 2.5rem;
}

.cuivre-footer__inner {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.8rem 2rem;
}

.cuivre-footer__brand {
  font-family: var(--cuivre-font-display);
  font-weight: 700;
  font-size: 1.05rem;
}

.cuivre-footer__meta {
  font-family: var(--cuivre-font-sans);
  font-size: 0.78rem;
  letter-spacing: 0.04em;
  color: color-mix(in srgb, white 65%, transparent);
}

/* ---- Intro (manchette) ---- */

.cuivre--boot [data-cuivre-intro] {
  opacity: 0;
  transform: translateY(14px);
}

.cuivre--ready [data-cuivre-intro] {
  opacity: 1;
  transform: none;
  transition:
    opacity 0.8s ease var(--cuivre-intro-delay, 0ms),
    transform 0.8s cubic-bezier(0.22, 1, 0.36, 1) var(--cuivre-intro-delay, 0ms);
}

.cuivre--boot .cuivre-hero__rule {
  transform: scaleX(0);
}

.cuivre--ready .cuivre-hero__rule {
  transform: scaleX(1);
  transition: transform 1s cubic-bezier(0.22, 1, 0.36, 1) 60ms;
}

/* ---- Reveals au scroll ---- */

.cuivre--js [data-cuivre-reveal] {
  opacity: 0;
  transform: translateY(22px);
  transition:
    opacity 0.75s ease,
    transform 0.75s cubic-bezier(0.22, 1, 0.36, 1);
  transition-delay: var(--cuivre-reveal-delay, 0ms);
}

.cuivre--js [data-cuivre-reveal].is-inked {
  opacity: 1;
  transform: none;
}

/* ---- Reduced motion : tout visible, rien n'anime ---- */

@media (prefers-reduced-motion: reduce) {
  .cuivre--boot [data-cuivre-intro],
  .cuivre--boot .cuivre-hero__rule {
    opacity: 1;
    transform: none;
  }

  .cuivre--ready [data-cuivre-intro],
  .cuivre--ready .cuivre-hero__rule {
    transition: none;
  }

  .cuivre--js [data-cuivre-reveal] {
    opacity: 1;
    transform: none;
    transition: none;
  }

  .cuivre-bar {
    transition: none;
  }
}
</style>
