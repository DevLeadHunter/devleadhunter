<template>
  <section v-if="zone.city" class="lumen-zone" aria-label="Zone d'intervention">
    <div class="lumen-container lumen-zone__inner" data-lumen-reveal>
      <div class="lumen-zone__radar" aria-hidden="true">
        <span class="lumen-zone__ring lumen-zone__ring--1"></span>
        <span class="lumen-zone__ring lumen-zone__ring--2"></span>
        <span class="lumen-zone__ring lumen-zone__ring--3"></span>
        <span class="lumen-zone__sweep"></span>
        <span class="lumen-zone__dot"></span>
      </div>

      <div class="lumen-zone__copy">
        <p class="lumen-kicker">{{ zone.heading }}</p>
        <p class="lumen-zone__city">{{ zone.city }}</p>
        <p v-if="zone.areaLabel" class="lumen-zone__area">{{ zone.areaLabel }}</p>
        <p v-if="zone.note" class="lumen-zone__note">{{ zone.note }}</p>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Zone d'intervention : radar concentrique avec balayage lumineux
 * centré sur la ville de l'artisan — un repère géographique sans carte.
 */
import type { LumenZoneContent } from '../types'

defineProps<{
  zone: LumenZoneContent
}>()
</script>

<style scoped>
.lumen-zone {
  border-block: 1px solid var(--lumen-line);
  background: linear-gradient(180deg, transparent, color-mix(in srgb, white 2%, transparent) 50%, transparent);
  overflow: hidden;
}

.lumen-zone__inner {
  display: grid;
  gap: 2.4rem;
  align-items: center;
  padding-block: 3.6rem;
}

@media (min-width: 768px) {
  .lumen-zone__inner {
    grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
    gap: 3.5rem;
  }
}

.lumen-zone__radar {
  position: relative;
  width: min(100%, 300px);
  aspect-ratio: 1;
  margin-inline: auto;
}

.lumen-zone__ring {
  position: absolute;
  inset: 0;
  border: 1px solid color-mix(in srgb, white 12%, transparent);
  border-radius: 9999px;
}

.lumen-zone__ring--2 {
  inset: 17%;
  border-color: color-mix(in srgb, white 9%, transparent);
}

.lumen-zone__ring--3 {
  inset: 34%;
  border-color: color-mix(in srgb, var(--lumen-yellow) 25%, transparent);
}

.lumen-zone__sweep {
  position: absolute;
  inset: 0;
  border-radius: 9999px;
  background: conic-gradient(from 0deg, color-mix(in srgb, var(--lumen-yellow) 20%, transparent), transparent 26%);
  animation: lumen-sweep 7s linear infinite;
}

.lumen-zone__dot {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 11px;
  height: 11px;
  margin: -5.5px 0 0 -5.5px;
  border-radius: 9999px;
  background: var(--lumen-yellow);
  box-shadow: 0 0 18px 3px color-mix(in srgb, var(--lumen-yellow) 60%, transparent);
}

.lumen-zone__city {
  margin-top: 1rem;
  font-family: var(--lumen-font-display);
  font-weight: 700;
  font-size: clamp(1.9rem, 4.4vw, 3rem);
  text-transform: uppercase;
  line-height: 1.05;
  color: var(--lumen-text);
}

.lumen-zone__area {
  margin-top: 0.7rem;
  font-family: var(--lumen-font-mono);
  font-size: 0.85rem;
  letter-spacing: 0.1em;
  color: var(--lumen-yellow);
}

.lumen-zone__note {
  margin-top: 1.1rem;
  max-width: 30rem;
  font-size: 0.92rem;
  line-height: 1.65;
  color: var(--lumen-muted);
}

@keyframes lumen-sweep {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .lumen-zone__sweep {
    animation: none;
    opacity: 0.35;
  }
}
</style>
