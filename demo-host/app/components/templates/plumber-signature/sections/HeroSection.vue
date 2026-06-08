<template>
  <section class="hero">
    <div class="hero-grid">
      <div class="hero-lead">
        <p class="eyebrow reveal" data-reveal>
          <span class="eyebrow-bar"></span>
          {{ hero.badge || 'Artisan plombier' }}<template v-if="city"> · {{ city }}</template>
        </p>
        <h1 class="hero-title reveal" data-reveal style="--d: 80ms">
          {{ hero.title || businessName }}
        </h1>
        <p class="hero-sub reveal" data-reveal style="--d: 160ms">
          {{ hero.subtitle || 'Dépannage, recherche de fuite et rénovation — un travail soigné, garanti, au juste prix.' }}
        </p>
        <div class="hero-actions reveal" data-reveal style="--d: 240ms">
          <a v-if="phone" :href="`tel:${phoneHref}`" class="btn btn-signal">
            <svg viewBox="0 0 24 24" class="ico" aria-hidden="true" v-html="icon('phone')" />
            <span>{{ hero.cta_label || 'Appeler maintenant' }}</span>
          </a>
          <a href="#contact" class="btn btn-ghost">Demander un devis</a>
        </div>
        <ul class="hero-points reveal" data-reveal style="--d: 320ms">
          <li v-for="(p, i) in heroPoints" :key="i">
            <svg viewBox="0 0 24 24" class="tick" aria-hidden="true" v-html="icon('check')" />
            {{ p }}
          </li>
        </ul>
      </div>

      <div class="hero-media reveal" data-reveal style="--d: 200ms">
        <div class="hero-frame">
          <img
            :src="img(hero.image as string, 1100, 1300)"
            :alt="`Réalisation de ${businessName}`"
            class="hero-img"
            data-parallax
            loading="eager"
            decoding="async"
          />
          <div class="hero-badge">
            <span class="hero-badge-dot" aria-hidden="true"></span>
            Disponible aujourd'hui
          </div>
        </div>
        <div class="hero-chip">
          <span class="hero-chip-val">{{ heroChip.value }}</span>
          <span class="hero-chip-label">{{ heroChip.label }}</span>
        </div>
      </div>
    </div>

    <!-- marquee éditorial des prestations -->
    <div class="marquee" aria-hidden="true">
      <div class="marquee-track">
        <span v-for="(w, i) in marqueeWords" :key="`a-${i}`" class="marquee-word">
          {{ w }}<span class="marquee-sep">/</span>
        </span>
        <span v-for="(w, i) in marqueeWords" :key="`b-${i}`" class="marquee-word">
          {{ w }}<span class="marquee-sep">/</span>
        </span>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { HeroBlock } from '../types'
import { icon, img } from '../utils'

defineProps<{
  hero: HeroBlock
  businessName: string
  city: string
  phone: string
  phoneHref: string
  heroPoints: string[]
  heroChip: { value: string; label: string }
  marqueeWords: string[]
}>()
</script>

<style scoped>
/* ════════════ Hero ════════════ */
.hero {
  position: relative;
  max-width: 1240px;
  margin: 0 auto;
  padding: clamp(3rem, 7vw, 6rem) 1.5rem 0;
}
.hero::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 120%;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(60% 50% at 78% 18%, color-mix(in srgb, var(--brand) 16%, transparent), transparent 70%),
    radial-gradient(45% 40% at 8% 6%, color-mix(in srgb, var(--signal) 9%, transparent), transparent 70%);
}
.hero-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: clamp(2rem, 5vw, 4rem);
  align-items: center;
}
.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--brand);
}
.eyebrow-bar {
  width: 1.7rem;
  height: 2px;
  background: var(--brand);
}
.hero-title {
  font-family: 'Bricolage Grotesque', 'Archivo', sans-serif;
  font-weight: 700;
  font-size: clamp(2.7rem, 6.2vw, 5rem);
  line-height: 0.98;
  letter-spacing: -0.035em;
  margin: 1.2rem 0 0;
  text-wrap: balance;
}
.hero-sub {
  font-size: clamp(1.05rem, 1.5vw, 1.22rem);
  color: var(--ink-soft);
  max-width: 38ch;
  margin: 1.3rem 0 0;
}
.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
  margin-top: 2rem;
}
.hero-points {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 1.2rem;
  margin-top: 1.8rem;
}
.hero-points li {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.92rem;
  font-weight: 550;
  color: var(--ink-soft);
}
.hero-points .tick {
  width: 1.1rem;
  height: 1.1rem;
  color: var(--brand);
  stroke-width: 2.4;
}

.hero-media {
  position: relative;
}
.hero-frame {
  position: relative;
  border-radius: 22px;
  overflow: hidden;
  aspect-ratio: 5 / 6;
  box-shadow: 0 40px 80px -40px color-mix(in srgb, var(--ink) 55%, transparent);
}
.hero-img {
  width: 100%;
  height: 112%;
  object-fit: cover;
  display: block;
  will-change: transform;
}
.hero-badge {
  position: absolute;
  top: 1rem;
  left: 1rem;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  background: color-mix(in srgb, var(--ink) 82%, transparent);
  color: #fff;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 0.45rem 0.8rem;
  border-radius: 999px;
  backdrop-filter: blur(4px);
}
.hero-badge-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #3ad29f;
}
.hero-chip {
  position: absolute;
  right: -0.6rem;
  bottom: -1rem;
  background: var(--paper);
  border: 1px solid var(--hair);
  border-radius: 16px;
  padding: 0.9rem 1.2rem;
  box-shadow: 0 20px 40px -22px color-mix(in srgb, var(--ink) 50%, transparent);
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.hero-chip-val {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700;
  font-size: 1.5rem;
  letter-spacing: -0.02em;
  color: var(--brand);
  font-variant-numeric: tabular-nums;
}
.hero-chip-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--ink-soft);
}

/* marquee */
.marquee {
  position: relative;
  z-index: 1;
  margin-top: clamp(2.5rem, 5vw, 4rem);
  border-top: 1px solid var(--hair);
  border-bottom: 1px solid var(--hair);
  overflow: hidden;
  --gap: 2.5rem;
}
.marquee-track {
  display: flex;
  gap: var(--gap);
  width: max-content;
  padding: 1rem 0;
  animation: marquee 32s linear infinite;
}
.marquee:hover .marquee-track {
  animation-play-state: paused;
}
.marquee-word {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 600;
  font-size: clamp(1.1rem, 2vw, 1.5rem);
  letter-spacing: -0.01em;
  color: color-mix(in srgb, var(--ink) 40%, var(--paper));
  display: inline-flex;
  align-items: center;
  gap: var(--gap);
  white-space: nowrap;
}
.marquee-sep {
  color: var(--signal);
}
@keyframes marquee {
  to {
    transform: translateX(calc(-50% - var(--gap) / 2));
  }
}

/* ════════════ Responsive ════════════ */
@media (max-width: 980px) {
  .hero-grid {
    grid-template-columns: 1fr;
  }
  .hero-media {
    max-width: 460px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .marquee-track {
    animation: none;
  }
}
</style>
