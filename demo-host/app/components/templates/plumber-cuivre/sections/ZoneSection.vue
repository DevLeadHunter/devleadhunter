<template>
  <section v-if="zone.city" class="cuivre-zone" aria-label="Secteur d'intervention">
    <div class="cuivre-container cuivre-zone__inner" data-cuivre-reveal>
      <p class="cuivre-eyebrow cuivre-zone__eyebrow"><span class="cuivre-eyebrow__num">06</span>{{ zone.heading }}</p>

      <p class="cuivre-zone__city-wrap">
        <span class="cuivre-zone__city">
          {{ zone.city }}
          <svg class="cuivre-zone__circle" viewBox="0 0 300 110" preserveAspectRatio="none" aria-hidden="true">
            <path
              d="M150 8 C 236 4, 292 26, 291 55 C 290 88, 216 104, 146 102 C 74 100, 10 86, 9 54 C 8 24, 70 8, 128 7"
              pathLength="1"
            />
          </svg>
        </span>
      </p>

      <p v-if="zone.areaLabel" class="cuivre-zone__area">{{ zone.areaLabel }}</p>
      <p v-if="zone.note" class="cuivre-zone__note">{{ zone.note }}</p>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Secteur d'intervention : la ville en très grande serif, encerclée d'un
 * trait cuivre « au crayon » qui se dessine à l'apparition — comme un
 * repère entouré sur une carte.
 */
import type { CuivreZoneContent } from '../types'

defineProps<{
  zone: CuivreZoneContent
}>()
</script>

<style scoped>
.cuivre-zone {
  margin-top: 5.5rem;
  padding-block: 3.8rem;
  border-block: 1px solid var(--cuivre-rule);
  background: linear-gradient(180deg, transparent, var(--cuivre-tint) 55%, transparent);
  text-align: center;
}

.cuivre-zone__eyebrow {
  justify-content: center;
}

.cuivre-zone__city-wrap {
  margin-top: 1.4rem;
}

.cuivre-zone__city {
  position: relative;
  display: inline-block;
  padding: 0.4rem 2.2rem;
  font-family: var(--cuivre-font-display);
  font-weight: 700;
  font-size: clamp(2.4rem, 7vw, 4.4rem);
  line-height: 1.05;
  color: var(--cuivre-ink);
}

.cuivre-zone__circle {
  position: absolute;
  inset: -6% -3%;
  width: 106%;
  height: 112%;
  overflow: visible;
  pointer-events: none;
}

.cuivre-zone__circle path {
  fill: none;
  stroke: var(--cuivre-blue);
  stroke-width: 2.4;
  stroke-linecap: round;
  vector-effect: non-scaling-stroke;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  transition: stroke-dashoffset 1.1s cubic-bezier(0.5, 0, 0.2, 1) 0.25s;
}

[data-cuivre-reveal].is-inked .cuivre-zone__circle path {
  stroke-dashoffset: 0;
}

.cuivre-zone__area {
  margin-top: 0.9rem;
  font-family: var(--cuivre-font-sans);
  font-weight: 600;
  font-size: 0.78rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--cuivre-blue);
}

.cuivre-zone__note {
  margin: 0.9rem auto 0;
  max-width: 28rem;
  font-family: var(--cuivre-font-sans);
  font-size: 0.93rem;
  color: var(--cuivre-muted);
}

@media (prefers-reduced-motion: reduce) {
  .cuivre-zone__circle path {
    stroke-dashoffset: 0;
    transition: none;
  }
}
</style>
