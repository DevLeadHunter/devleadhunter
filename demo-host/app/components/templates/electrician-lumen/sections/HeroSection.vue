<template>
  <header class="lumen-hero" aria-label="Présentation">
    <div class="lumen-hero__glow" data-lumen-glow aria-hidden="true"></div>
    <div class="lumen-hero__grid" aria-hidden="true"></div>

    <div class="lumen-container lumen-hero__inner">
      <div class="lumen-hero__copy">
        <p class="lumen-hero__badge" data-lumen-boot="1">
          <span class="lumen-hero__badge-dot" aria-hidden="true"></span>
          {{ hero.badge }}
        </p>

        <h1 class="lumen-hero__title" data-lumen-boot="2">{{ hero.title || businessName }}</h1>

        <p v-if="hero.subtitle" class="lumen-hero__subtitle" data-lumen-boot="3">{{ hero.subtitle }}</p>

        <div class="lumen-hero__actions" data-lumen-boot="4">
          <a v-if="hero.phone" class="lumen-btn lumen-btn--primary" :href="`tel:${hero.phone}`">
            <LumenIcon name="phone" class="lumen-btn__icon" />
            {{ hero.ctaCallLabel }}
          </a>
          <a class="lumen-btn lumen-btn--ghost" href="#contact">{{ hero.ctaQuoteLabel }}</a>
        </div>

        <p v-if="hero.phone" class="lumen-hero__phone" data-lumen-boot="5">
          <span class="lumen-hero__phone-label">Ligne directe</span>
          <a :href="`tel:${hero.phone}`" class="lumen-hero__phone-number">{{ hero.phone }}</a>
        </p>

        <ul v-if="hero.points.length" class="lumen-hero__points" data-lumen-boot="6">
          <li v-for="point in hero.points" :key="point" class="lumen-hero__point">
            <LumenIcon name="check" class="lumen-hero__point-icon" />
            {{ point }}
          </li>
        </ul>
      </div>

      <div class="lumen-hero__art" data-lumen-boot="7">
        <figure v-if="hero.image" class="lumen-hero__frame">
          <img :src="hero.image" :alt="`Réalisation — ${hero.title || businessName}`" class="lumen-hero__photo" loading="eager" />
          <figcaption class="lumen-hero__caption">
            <span class="lumen-hero__caption-dot" aria-hidden="true"></span>
            {{ hero.imageCaption || 'Chantier récent' }}
          </figcaption>
        </figure>

        <div v-else class="lumen-hero__frame lumen-hero__frame--circuit" aria-hidden="true">
          <svg viewBox="0 0 460 380" class="lumen-hero__circuit" fill="none">
            <!-- Pistes du circuit -->
            <g class="lumen-hero__traces" stroke-width="1.5">
              <path d="M40 60 H150 V140 H230" />
              <path d="M420 80 H330 V150 H230 V190" />
              <path d="M40 320 H120 V240 H180 V190 H230" />
              <path d="M420 300 H340 V230 H280 V190" />
              <path d="M230 40 V140" />
              <path d="M230 240 V340" />
            </g>
            <!-- Flux animé -->
            <g class="lumen-hero__flows" stroke-width="1.5">
              <path d="M40 60 H150 V140 H230" />
              <path d="M40 320 H120 V240 H180 V190 H230" />
            </g>
            <!-- Nœuds -->
            <g class="lumen-hero__nodes">
              <circle cx="40" cy="60" r="4" />
              <circle cx="420" cy="80" r="4" />
              <circle cx="40" cy="320" r="4" />
              <circle cx="420" cy="300" r="4" />
              <circle cx="230" cy="40" r="4" />
              <circle cx="230" cy="340" r="4" />
            </g>
            <!-- Module central : disjoncteur -->
            <g class="lumen-hero__module">
              <rect x="180" y="140" width="100" height="100" rx="6" class="lumen-hero__module-plate" />
              <rect x="205" y="158" width="50" height="64" rx="4" class="lumen-hero__module-slot" />
              <rect x="219" y="166" width="22" height="30" rx="3" class="lumen-hero__module-lever" />
              <text x="230" y="212" text-anchor="middle" class="lumen-hero__module-text">ON</text>
            </g>
          </svg>
          <p class="lumen-hero__caption">
            <span class="lumen-hero__caption-dot" aria-hidden="true"></span>
            Installation sous tension — protégée
          </p>
        </div>
      </div>
    </div>
  </header>
</template>

<script lang="ts" setup>
/**
 * Hero « allumage » de la template 'electrician-lumen'.
 * Colonne gauche : badge, nom de l'entreprise, promesse et CTA.
 * Colonne droite : photo de chantier (enrichissement) ou, à défaut,
 * illustration circuit dessinée en SVG pour rester impeccable sans photo.
 */
import LumenIcon from './LumenIcon.vue'
import type { LumenHeroContent } from '../types'

defineProps<{
  hero: LumenHeroContent
  businessName: string
}>()
</script>

<style scoped>
.lumen-hero {
  position: relative;
  padding: calc(5.5rem + var(--lumen-nav-height)) 0 4.5rem;
  overflow: hidden;
}

.lumen-hero__glow {
  position: absolute;
  top: -14rem;
  left: -10rem;
  width: 44rem;
  height: 44rem;
  border-radius: 9999px;
  background: radial-gradient(circle, color-mix(in srgb, var(--lumen-yellow) 16%, transparent) 0%, transparent 62%);
  pointer-events: none;
}

.lumen-hero__grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(color-mix(in srgb, white 3%, transparent) 1px, transparent 1px),
    linear-gradient(90deg, color-mix(in srgb, white 3%, transparent) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: radial-gradient(ellipse 90% 80% at 40% 20%, black 30%, transparent 75%);
  pointer-events: none;
}

.lumen-hero__inner {
  position: relative;
  display: grid;
  gap: 3.5rem;
  align-items: center;
}

@media (min-width: 1024px) {
  .lumen-hero__inner {
    grid-template-columns: minmax(0, 7fr) minmax(0, 5fr);
    gap: 4.5rem;
  }
}

.lumen-hero__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  font-family: var(--lumen-font-mono);
  font-size: 0.78rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--lumen-yellow);
  border: 1px solid color-mix(in srgb, var(--lumen-yellow) 30%, transparent);
  background: color-mix(in srgb, var(--lumen-yellow) 6%, transparent);
  padding: 0.5rem 0.9rem;
  clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
}

.lumen-hero__badge-dot {
  width: 7px;
  height: 7px;
  background: var(--lumen-yellow);
  box-shadow: 0 0 10px 1px color-mix(in srgb, var(--lumen-yellow) 80%, transparent);
  animation: lumen-blink 2.4s ease-in-out infinite;
}

.lumen-hero__title {
  margin-top: 1.4rem;
  font-family: var(--lumen-font-display);
  font-weight: 700;
  font-size: clamp(2.5rem, 6.2vw, 4.4rem);
  line-height: 1.02;
  text-transform: uppercase;
  letter-spacing: 0.005em;
  color: var(--lumen-text);
  text-wrap: balance;
  text-shadow: 0 0 46px color-mix(in srgb, var(--lumen-yellow) 22%, transparent);
}

.lumen-hero__subtitle {
  margin-top: 1.4rem;
  max-width: 34rem;
  font-size: clamp(1rem, 1.6vw, 1.13rem);
  line-height: 1.65;
  color: var(--lumen-muted);
}

.lumen-hero__actions {
  margin-top: 2.2rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.9rem;
}

.lumen-hero__phone {
  margin-top: 1.6rem;
  display: flex;
  align-items: baseline;
  gap: 0.9rem;
}

.lumen-hero__phone-label {
  font-family: var(--lumen-font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--lumen-muted);
}

.lumen-hero__phone-number {
  font-family: var(--lumen-font-mono);
  font-weight: 600;
  font-size: clamp(1.2rem, 2.4vw, 1.55rem);
  color: var(--lumen-text);
  text-decoration: none;
  transition: color 0.2s ease;
}

.lumen-hero__phone-number:hover {
  color: var(--lumen-yellow);
}

.lumen-hero__points {
  margin-top: 1.9rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem 1.6rem;
  list-style: none;
  padding: 0;
}

.lumen-hero__point {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: var(--lumen-muted);
}

.lumen-hero__point-icon {
  width: 15px;
  height: 15px;
  color: var(--lumen-yellow);
}

/* ---- Colonne art ---- */

.lumen-hero__art {
  position: relative;
}

.lumen-hero__frame {
  position: relative;
  border: 1px solid var(--lumen-line);
  background: var(--lumen-panel);
  padding: 0.9rem;
  clip-path: polygon(16px 0, 100% 0, 100% calc(100% - 16px), calc(100% - 16px) 100%, 0 100%, 0 16px);
  box-shadow: 0 24px 70px -30px color-mix(in srgb, var(--lumen-yellow) 22%, transparent);
}

.lumen-hero__photo {
  display: block;
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  filter: saturate(0.94) contrast(1.04);
}

.lumen-hero__caption {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  margin: 0;
  padding: 0.8rem 0.3rem 0.1rem;
  font-family: var(--lumen-font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--lumen-muted);
}

.lumen-hero__caption-dot {
  width: 6px;
  height: 6px;
  background: var(--lumen-amber);
  box-shadow: 0 0 8px 1px color-mix(in srgb, var(--lumen-amber) 75%, transparent);
}

/* ---- Illustration circuit (fallback sans photo) ---- */

.lumen-hero__frame--circuit {
  background:
    radial-gradient(circle at 50% 45%, color-mix(in srgb, var(--lumen-yellow) 5%, transparent) 0%, transparent 60%),
    var(--lumen-panel);
}

.lumen-hero__circuit {
  display: block;
  width: 100%;
  height: auto;
}

.lumen-hero__traces path {
  stroke: color-mix(in srgb, white 13%, transparent);
}

.lumen-hero__flows path {
  stroke: var(--lumen-yellow);
  stroke-dasharray: 26 300;
  stroke-dashoffset: 326;
  opacity: 0.85;
  filter: drop-shadow(0 0 4px color-mix(in srgb, var(--lumen-yellow) 70%, transparent));
  animation: lumen-flow 4.2s linear infinite;
}

.lumen-hero__flows path:nth-child(2) {
  animation-delay: 2.1s;
}

.lumen-hero__nodes circle {
  fill: color-mix(in srgb, white 22%, transparent);
}

.lumen-hero__module-plate {
  fill: var(--lumen-raised);
  stroke: var(--lumen-line);
}

.lumen-hero__module-slot {
  fill: var(--lumen-night);
  stroke: color-mix(in srgb, white 16%, transparent);
}

.lumen-hero__module-lever {
  fill: var(--lumen-yellow);
  filter: drop-shadow(0 0 7px color-mix(in srgb, var(--lumen-yellow) 65%, transparent));
}

.lumen-hero__module-text {
  fill: var(--lumen-yellow);
  font-family: var(--lumen-font-mono);
  font-size: 11px;
  letter-spacing: 0.2em;
}

@keyframes lumen-flow {
  to {
    stroke-dashoffset: 0;
  }
}

@keyframes lumen-blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}

@media (prefers-reduced-motion: reduce) {
  .lumen-hero__flows path,
  .lumen-hero__badge-dot {
    animation: none;
  }
}
</style>
