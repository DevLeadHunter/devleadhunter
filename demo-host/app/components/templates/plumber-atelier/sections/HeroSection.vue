<template>
  <section class="hero">
    <div class="hero-grid">
      <div class="hero-lead">
        <p class="eyebrow reveal" data-reveal>
          <span class="eyebrow-mark"></span>
          {{ hero.badge || 'Dépannage 7j/7' }}<template v-if="city"> · {{ city }}</template>
        </p>
        <h1 class="hero-title reveal" data-reveal style="--d: 90ms">
          {{ hero.title || businessName }}
        </h1>
        <p v-if="hero.subtitle" class="hero-sub reveal" data-reveal style="--d: 180ms">
          {{ hero.subtitle }}
        </p>
        <div class="hero-actions reveal" data-reveal style="--d: 270ms">
          <a v-if="phone" :href="`tel:${phone}`" class="btn btn-brass">
            <svg viewBox="0 0 24 24" class="ico" aria-hidden="true"><path d="M3 5a2 2 0 0 1 2-2h2.4a1 1 0 0 1 1 .8l.9 4a1 1 0 0 1-.5 1.1L7.5 10a11 11 0 0 0 5.5 5.5l1.1-1.3a1 1 0 0 1 1.1-.5l4 .9a1 1 0 0 1 .8 1V18a2 2 0 0 1-2 2A15 15 0 0 1 3 5Z"/></svg>
            <span>{{ hero.cta_label || 'Appeler' }}<template v-if="phone"> — {{ phone }}</template></span>
          </a>
          <a href="#contact" class="btn btn-ink">Devis gratuit</a>
        </div>
        <!-- règle technique graduée -->
        <svg class="hero-ruler reveal" data-reveal style="--d: 360ms" viewBox="0 0 600 16" preserveAspectRatio="none" aria-hidden="true">
          <line x1="0" y1="8" x2="600" y2="8" class="ruler-base" />
          <g class="ruler-ticks">
            <line v-for="t in 25" :key="t" :x1="(t - 1) * 25" y1="8" :x2="(t - 1) * 25" :y2="(t - 1) % 5 === 0 ? 0 : 4" />
          </g>
        </svg>
      </div>

      <!-- Fiche d'intervention (carte spec) -->
      <aside class="hero-card reveal" data-reveal style="--d: 320ms">
        <div class="card-corner card-corner-tl"></div>
        <div class="card-corner card-corner-br"></div>
        <p class="card-label">Fiche d'intervention</p>
        <dl class="card-rows">
          <div class="card-row">
            <dt>Disponibilité</dt>
            <dd>{{ hero.badge || 'Urgences 7j/7' }}</dd>
          </div>
          <div v-if="city" class="card-row">
            <dt>Zone</dt>
            <dd>{{ city }}</dd>
          </div>
          <div v-if="phone" class="card-row">
            <dt>Ligne directe</dt>
            <dd>{{ phone }}</dd>
          </div>
          <div class="card-row">
            <dt>Devis</dt>
            <dd>Gratuit · sous 2h</dd>
          </div>
        </dl>
        <a v-if="phone" :href="`tel:${phone}`" class="card-call">Appeler l'atelier</a>
      </aside>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { HeroBlock } from '../types'

defineProps<{
  hero: HeroBlock
  businessName: string
  phone: string
  city: string
}>()
</script>

<style scoped>
.hero {
  max-width: 1200px;
  margin: 0 auto;
  padding: clamp(3.5rem, 8vw, 7rem) 1.5rem clamp(2.5rem, 5vw, 4rem);
}
.hero-grid {
  display: grid;
  grid-template-columns: 7fr 5fr;
  gap: clamp(2rem, 5vw, 4.5rem);
  align-items: end;
}
.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.74rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: var(--brass);
}
.eyebrow-mark {
  width: 1.6rem;
  height: 2px;
  background: var(--brass);
}
.hero-title {
  font-family: 'Fraunces', serif;
  font-weight: 600;
  font-size: clamp(2.6rem, 6.2vw, 5.2rem);
  line-height: 0.98;
  letter-spacing: -0.02em;
  margin: 1.4rem 0 0;
  text-wrap: balance;
}
.hero-sub {
  font-size: clamp(1.05rem, 1.5vw, 1.25rem);
  color: var(--ink-soft);
  max-width: 34ch;
  margin: 1.4rem 0 0;
}
.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.9rem;
  margin-top: 2.2rem;
}
.hero-ruler {
  width: 100%;
  height: 16px;
  margin-top: 2.6rem;
  color: var(--ink);
  opacity: 0.5;
}
.ruler-base {
  stroke-width: 1;
}
.ruler-ticks line {
  stroke-width: 1;
}

/* Fiche d'intervention */
.hero-card {
  position: relative;
  background: var(--paper-2);
  border: 1px solid var(--hair);
  padding: 1.6rem 1.5rem 1.5rem;
}
.card-corner {
  position: absolute;
  width: 12px;
  height: 12px;
  border: 1.5px solid var(--brass);
}
.card-corner-tl {
  top: -1px;
  left: -1px;
  border-right: 0;
  border-bottom: 0;
}
.card-corner-br {
  bottom: -1px;
  right: -1px;
  border-left: 0;
  border-top: 0;
}
.card-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--ink-soft);
  margin-bottom: 1rem;
}
.card-rows {
  display: flex;
  flex-direction: column;
}
.card-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 1rem;
  padding: 0.7rem 0;
  border-top: 1px solid var(--hair);
}
.card-row dt {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-soft);
}
.card-row dd {
  font-family: 'Fraunces', serif;
  font-weight: 600;
  font-size: 1rem;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.card-call {
  display: block;
  text-align: center;
  margin-top: 1.2rem;
  padding: 0.7rem;
  font-weight: 600;
  font-size: 0.9rem;
  background: var(--ink);
  color: var(--paper);
  transition: background 0.18s ease;
}
.card-call:hover {
  background: var(--brass);
}

/* ════════════ Responsive ════════════ */
@media (max-width: 860px) {
  .hero-grid {
    grid-template-columns: 1fr;
  }
  .hero-grid {
    align-items: start;
  }
}
</style>
