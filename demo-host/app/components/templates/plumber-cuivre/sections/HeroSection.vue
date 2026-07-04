<template>
  <header class="cuivre-hero" aria-label="Présentation">
    <div class="cuivre-hero__halo" aria-hidden="true"></div>

    <!-- Manchette -->
    <div class="cuivre-container">
      <div class="cuivre-hero__topline" data-cuivre-intro :style="{ '--cuivre-intro-delay': '0ms' }">
        <p class="cuivre-hero__badge">
          <CuivreGlyph name="drop" class="cuivre-hero__badge-icon" />
          {{ hero.badge }}
        </p>
        <a v-if="hero.phone" :href="`tel:${hero.phone}`" class="cuivre-hero__topline-phone">
          <CuivreGlyph name="phone" class="cuivre-hero__topline-icon" />
          {{ hero.phone }}
        </a>
      </div>

      <div class="cuivre-hero__rule cuivre-hero__rule--wave" aria-hidden="true"></div>

      <h1 class="cuivre-hero__masthead" data-cuivre-intro :style="{ '--cuivre-intro-delay': '90ms' }">
        {{ hero.title || businessName }}
      </h1>

      <nav class="cuivre-hero__nav" data-cuivre-intro :style="{ '--cuivre-intro-delay': '180ms' }" aria-label="Navigation principale">
        <a href="#depannage" class="cuivre-hero__nav-link">Dépannage</a>
        <span class="cuivre-hero__nav-dot" aria-hidden="true">·</span>
        <a href="#services" class="cuivre-hero__nav-link">Services</a>
        <span class="cuivre-hero__nav-dot" aria-hidden="true">·</span>
        <a href="#savoir-faire" class="cuivre-hero__nav-link">Savoir-faire</a>
        <span class="cuivre-hero__nav-dot" aria-hidden="true">·</span>
        <a href="#artisan" class="cuivre-hero__nav-link">L'artisan</a>
        <span class="cuivre-hero__nav-dot" aria-hidden="true">·</span>
        <a href="#faq" class="cuivre-hero__nav-link">FAQ</a>
        <span class="cuivre-hero__nav-dot" aria-hidden="true">·</span>
        <a href="#contact" class="cuivre-hero__nav-link">Contact</a>
      </nav>

      <div class="cuivre-hero__rule" aria-hidden="true"></div>
    </div>

    <!-- Corps du hero -->
    <div class="cuivre-container cuivre-hero__body">
      <div class="cuivre-hero__copy">
        <p v-if="hero.subtitle" class="cuivre-hero__lead" data-cuivre-intro :style="{ '--cuivre-intro-delay': '270ms' }">
          {{ hero.subtitle }}
        </p>

        <div class="cuivre-hero__actions" data-cuivre-intro :style="{ '--cuivre-intro-delay': '360ms' }">
          <a v-if="hero.phone" class="cuivre-btn cuivre-btn--blue" :href="`tel:${hero.phone}`">
            <CuivreGlyph name="phone" class="cuivre-btn__icon" />
            {{ hero.ctaCallLabel }}
          </a>
          <a class="cuivre-btn cuivre-btn--ghost" href="#contact">{{ hero.ctaQuoteLabel }}</a>
        </div>

        <ul v-if="hero.points.length" class="cuivre-hero__points" data-cuivre-intro :style="{ '--cuivre-intro-delay': '450ms' }">
          <li v-for="point in hero.points" :key="point" class="cuivre-hero__point">
            <CuivreGlyph name="check" class="cuivre-hero__point-icon" />
            {{ point }}
          </li>
        </ul>
      </div>

      <div class="cuivre-hero__art" data-cuivre-intro :style="{ '--cuivre-intro-delay': '380ms' }">
        <figure v-if="hero.image" class="cuivre-hero__frame">
          <img :src="hero.image" :alt="`Réalisation — ${hero.title || businessName}`" class="cuivre-hero__photo" loading="eager" />
          <figcaption class="cuivre-hero__caption">
            <span class="cuivre-hero__caption-dot" aria-hidden="true"></span>
            {{ hero.imageCaption || 'Chantier récent' }}
          </figcaption>
        </figure>

        <div v-else class="cuivre-hero__frame cuivre-hero__frame--plate" aria-hidden="true">
          <svg viewBox="0 0 460 340" class="cuivre-hero__plate" fill="none">
            <!-- Mur (hachures) -->
            <g class="cuivre-hero__plate-ink" stroke-width="1.3">
              <path d="M70 40 V300" />
              <path d="M70 55 60 68M70 85 60 98M70 115 60 128M70 145 60 158M70 175 60 188M70 205 60 218M70 235 60 248M70 265 60 278" />
            </g>
            <!-- Réseau d'eau -->
            <g class="cuivre-hero__plate-blue" stroke-width="2.4">
              <path d="M70 90 H210" />
              <path d="M218 98 V210" />
              <path d="M226 218 H390" />
              <path d="M390 218 V264" />
            </g>
            <!-- Coudes & raccords -->
            <g class="cuivre-hero__plate-blue" stroke-width="2">
              <path d="M210 90a8 8 0 0 1 8 8" />
              <path d="M218 210a8 8 0 0 0 8 8" />
              <path d="M140 82v16M146 82v16" />
              <path d="M218 140h-8M218 146h-8" transform="rotate(90 214 143)" />
              <path d="M300 210v16M306 210v16" />
            </g>
            <!-- Vanne (volant) -->
            <g class="cuivre-hero__plate-ink" stroke-width="1.6">
              <circle cx="262" cy="192" r="14" />
              <path d="M262 178v-8M262 206v-8M248 192h-8M276 192h8M252 182l-5-5M272 182l5-5M252 202l-5 5M272 202l5 5" />
              <path d="M262 206 V218" />
            </g>
            <!-- Robinet + goutte -->
            <g class="cuivre-hero__plate-ink" stroke-width="1.6">
              <path d="M378 264h24M382 264v10h16v-10" />
            </g>
            <path class="cuivre-hero__plate-drop" d="M390 296c4.5 6 7.5 10.2 7.5 14a7.5 7.5 0 1 1-15 0c0-3.8 3-8 7.5-14Z" stroke-width="1.6" />
          </svg>
          <p class="cuivre-hero__caption">
            <span class="cuivre-hero__caption-dot" aria-hidden="true"></span>
            Réseau d'eau — pose dans les règles de l'art
          </p>
        </div>

        <!-- Badge rotatif -->
        <div class="cuivre-hero__seal" aria-hidden="true">
          <svg viewBox="0 0 120 120" class="cuivre-hero__seal-svg">
            <defs>
              <path id="cuivre-seal-circle" d="M60,60 m-44,0 a44,44 0 1,1 88,0 a44,44 0 1,1 -88,0" />
            </defs>
            <circle cx="60" cy="60" r="56" class="cuivre-hero__seal-ring" />
            <circle cx="60" cy="60" r="30" class="cuivre-hero__seal-ring cuivre-hero__seal-ring--inner" />
            <g class="cuivre-hero__seal-spin">
              <text class="cuivre-hero__seal-text">
                <textPath href="#cuivre-seal-circle" startOffset="0">devis gratuit · travail garanti · devis gratuit ·</textPath>
              </text>
            </g>
            <g class="cuivre-hero__seal-glyph" transform="translate(48 48)">
              <path d="M12 3.5c3.2 4.2 5.5 7.3 5.5 10.2a5.5 5.5 0 1 1-11 0c0-2.9 2.3-6 5.5-10.2Z" fill="none" stroke-width="1.6" />
            </g>
          </svg>
        </div>
      </div>
    </div>
  </header>
</template>

<script lang="ts" setup>
/**
 * Hero « manchette » de la template 'plumber-cuivre' (« Plombier Source ») :
 * bandeau du haut (badge goutte + téléphone), nom de l'entreprise en grande
 * display entre une vague et un filet, navigation d'ancres, puis lead, CTA
 * pilule et points de confiance. Colonne droite : photo de chantier encadrée
 * ou, sans photo, une planche du réseau d'eau — avec le badge rotatif
 * « devis gratuit · travail garanti ».
 */
import CuivreGlyph from './CuivreGlyph.vue'
import type { CuivreHeroContent } from '../types'

defineProps<{
  hero: CuivreHeroContent
  businessName: string
}>()
</script>

<style scoped>
.cuivre-hero {
  position: relative;
  padding-top: 2.2rem;
  overflow: hidden;
}

.cuivre-hero__halo {
  position: absolute;
  top: -16rem;
  right: -12rem;
  width: 42rem;
  height: 42rem;
  border-radius: 9999px;
  background: radial-gradient(circle, color-mix(in srgb, var(--cuivre-aqua) 14%, transparent) 0%, transparent 62%);
  pointer-events: none;
}

/* ---- Manchette ---- */

.cuivre-hero__topline {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  padding-bottom: 0.9rem;
}

.cuivre-hero__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.42rem 0.95rem;
  border-radius: 9999px;
  background: color-mix(in srgb, var(--cuivre-aqua) 13%, white);
  border: 1px solid color-mix(in srgb, var(--cuivre-aqua) 35%, transparent);
  font-family: var(--cuivre-font-display);
  font-weight: 700;
  font-size: 0.72rem;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  color: var(--cuivre-blue);
}

.cuivre-hero__badge-icon {
  width: 13px;
  height: 13px;
}

.cuivre-hero__topline-phone {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-family: var(--cuivre-font-sans);
  font-weight: 600;
  font-size: 0.85rem;
  white-space: nowrap;
  color: var(--cuivre-ink);
  text-decoration: none;
  transition: color 0.2s ease;
}

.cuivre-hero__topline-phone:hover {
  color: var(--cuivre-blue);
}

.cuivre-hero__topline-icon {
  width: 14px;
  height: 14px;
  color: var(--cuivre-blue);
}

.cuivre-hero__rule {
  height: 1px;
  background: var(--cuivre-rule);
  transform-origin: left;
}

/* La vague : même mécanique d'intro que les filets, rendu « eau » */
.cuivre-hero__rule.cuivre-hero__rule--wave {
  height: 9px;
  background: color-mix(in srgb, var(--cuivre-blue) 50%, transparent);
  mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='36' height='9' viewBox='0 0 36 9'%3E%3Cpath d='M0 6.5C4.5 6.5 4.5 2 9 2s4.5 4.5 9 4.5S22.5 2 27 2s4.5 4.5 9 4.5' fill='none' stroke='black' stroke-width='1.6' stroke-linecap='round'/%3E%3C/svg%3E");
  mask-repeat: repeat-x;
  mask-position: left center;
  -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='36' height='9' viewBox='0 0 36 9'%3E%3Cpath d='M0 6.5C4.5 6.5 4.5 2 9 2s4.5 4.5 9 4.5S22.5 2 27 2s4.5 4.5 9 4.5' fill='none' stroke='black' stroke-width='1.6' stroke-linecap='round'/%3E%3C/svg%3E");
  -webkit-mask-repeat: repeat-x;
  -webkit-mask-position: left center;
}

.cuivre-hero__masthead {
  margin: 0;
  padding: 1.5rem 0 1rem;
  font-family: var(--cuivre-font-display);
  font-weight: 800;
  font-size: clamp(2.5rem, 6.6vw, 4.7rem);
  line-height: 1.02;
  letter-spacing: -0.015em;
  text-align: center;
  color: var(--cuivre-ink);
  text-wrap: balance;
}

.cuivre-hero__nav {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: center;
  gap: 0.3rem 0.85rem;
  padding-bottom: 1rem;
}

.cuivre-hero__nav-link {
  font-family: var(--cuivre-font-display);
  font-weight: 600;
  font-size: 0.8rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--cuivre-muted);
  text-decoration: none;
  transition: color 0.2s ease;
}

.cuivre-hero__nav-link:hover {
  color: var(--cuivre-blue);
}

.cuivre-hero__nav-dot {
  color: color-mix(in srgb, var(--cuivre-blue) 40%, transparent);
}

/* ---- Corps ---- */

.cuivre-hero__body {
  position: relative;
  display: grid;
  gap: 3rem;
  align-items: center;
  padding-block: clamp(2.6rem, 6vw, 4.2rem) clamp(2.8rem, 6vw, 4.5rem);
}

@media (min-width: 1024px) {
  .cuivre-hero__body {
    grid-template-columns: minmax(0, 6.5fr) minmax(0, 5.5fr);
    gap: 5rem;
  }
}

.cuivre-hero__lead {
  font-family: var(--cuivre-font-display);
  font-weight: 500;
  font-size: clamp(1.3rem, 2.5vw, 1.8rem);
  line-height: 1.4;
  letter-spacing: -0.005em;
  color: var(--cuivre-ink);
  max-width: 32rem;
  text-wrap: balance;
}

.cuivre-hero__actions {
  margin-top: 2.1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.85rem;
}

.cuivre-hero__points {
  margin-top: 1.9rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem 1.5rem;
  list-style: none;
  padding: 0;
}

.cuivre-hero__point {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--cuivre-font-sans);
  font-size: 0.9rem;
  color: var(--cuivre-muted);
}

.cuivre-hero__point-icon {
  width: 14px;
  height: 14px;
  color: var(--cuivre-aqua);
}

/* ---- Colonne art ---- */

.cuivre-hero__art {
  position: relative;
  max-width: 34rem;
}

.cuivre-hero__frame {
  margin: 0;
  padding: 0.7rem;
  background: var(--cuivre-card);
  border: 1px solid var(--cuivre-rule);
  border-radius: 18px;
  box-shadow: 0 24px 50px -30px color-mix(in srgb, var(--cuivre-blue) 55%, transparent);
}

.cuivre-hero__photo {
  display: block;
  width: 100%;
  aspect-ratio: 5 / 4;
  object-fit: cover;
  border-radius: 12px;
  filter: saturate(1.02) contrast(1.02);
}

.cuivre-hero__frame--plate {
  background:
    radial-gradient(ellipse 80% 70% at 50% 40%, color-mix(in srgb, var(--cuivre-aqua) 7%, transparent), transparent 70%),
    var(--cuivre-card);
}

.cuivre-hero__plate {
  display: block;
  width: 100%;
  height: auto;
}

.cuivre-hero__plate-ink path,
.cuivre-hero__plate-ink circle {
  stroke: color-mix(in srgb, var(--cuivre-ink) 50%, transparent);
}

.cuivre-hero__plate-blue path {
  stroke: var(--cuivre-blue);
}

.cuivre-hero__plate-drop {
  stroke: var(--cuivre-aqua);
  fill: color-mix(in srgb, var(--cuivre-aqua) 18%, transparent);
}

.cuivre-hero__caption {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  margin: 0;
  padding: 0.7rem 0.45rem 0.15rem;
  font-family: var(--cuivre-font-sans);
  font-size: 0.84rem;
  color: var(--cuivre-muted);
}

.cuivre-hero__caption-dot {
  width: 8px;
  height: 8px;
  flex: none;
  border-radius: 9999px 9999px 9999px 2px;
  transform: rotate(45deg);
  background: var(--cuivre-aqua);
}

/* ---- Badge rotatif ---- */

.cuivre-hero__seal {
  position: absolute;
  top: -2.4rem;
  right: -1.2rem;
  width: clamp(92px, 10vw, 120px);
  filter: drop-shadow(0 8px 16px color-mix(in srgb, var(--cuivre-ink) 22%, transparent));
}

@media (max-width: 640px) {
  .cuivre-hero__seal {
    right: -0.4rem;
    top: -2rem;
  }
}

.cuivre-hero__seal-svg {
  display: block;
  width: 100%;
  height: auto;
}

.cuivre-hero__seal-ring {
  fill: var(--cuivre-card);
  stroke: var(--cuivre-blue);
  stroke-width: 1.6;
}

.cuivre-hero__seal-ring--inner {
  stroke: color-mix(in srgb, var(--cuivre-aqua) 65%, transparent);
  stroke-dasharray: 3 4;
}

.cuivre-hero__seal-spin {
  transform-origin: 60px 60px;
  animation: cuivre-seal-spin 28s linear infinite;
}

.cuivre-hero__seal-text {
  font-family: var(--cuivre-font-display);
  font-weight: 700;
  font-size: 10.5px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  fill: var(--cuivre-blue);
}

.cuivre-hero__seal-glyph path {
  stroke: var(--cuivre-aqua);
}

@keyframes cuivre-seal-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .cuivre-hero__seal-spin {
    animation: none;
  }
}
</style>
