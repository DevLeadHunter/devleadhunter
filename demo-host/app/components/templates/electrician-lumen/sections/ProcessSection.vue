<template>
  <section v-if="process.items.length" id="methode" class="lumen-section" aria-label="Méthode">
    <div class="lumen-container">
      <div class="lumen-section__head" data-lumen-reveal>
        <p class="lumen-kicker">Méthode</p>
        <h2 class="lumen-heading">{{ process.heading }}</h2>
        <p v-if="process.subheading" class="lumen-section__subheading">{{ process.subheading }}</p>
      </div>

      <ol class="lumen-process__grid">
        <li
          v-for="(step, index) in process.items"
          :key="step.title"
          class="lumen-process__step"
          data-lumen-reveal
          :style="{ '--lumen-reveal-delay': `${index * 110}ms` }"
        >
          <p class="lumen-process__number">
            {{ String(index + 1).padStart(2, '0') }}
            <span v-if="index < process.items.length - 1" class="lumen-process__wire" aria-hidden="true"></span>
          </p>
          <h3 class="lumen-process__title">{{ step.title }}</h3>
          <p class="lumen-process__description">{{ step.description }}</p>
        </li>
      </ol>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Process en 4 étapes : numéros mono lumineux reliés par un « fil »
 * pointillé qui matérialise le circuit de l'intervention.
 */
import type { LumenProcessContent } from '../types'

defineProps<{
  process: LumenProcessContent
}>()
</script>

<style scoped>
.lumen-process__grid {
  margin-top: 2.8rem;
  display: grid;
  gap: 2.2rem 1.4rem;
  list-style: none;
  padding: 0;
  counter-reset: none;
}

@media (min-width: 640px) {
  .lumen-process__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .lumen-process__grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.lumen-process__number {
  position: relative;
  display: flex;
  align-items: center;
  font-family: var(--lumen-font-mono);
  font-weight: 600;
  font-size: 1.7rem;
  color: var(--lumen-yellow);
  text-shadow: 0 0 20px color-mix(in srgb, var(--lumen-yellow) 40%, transparent);
}

.lumen-process__wire {
  flex: 1;
  height: 1px;
  margin-left: 1rem;
  background-image: linear-gradient(90deg, color-mix(in srgb, white 24%, transparent) 55%, transparent 0);
  background-size: 9px 1px;
  display: none;
}

@media (min-width: 1024px) {
  .lumen-process__wire {
    display: block;
  }
}

.lumen-process__title {
  margin-top: 0.9rem;
  font-family: var(--lumen-font-display);
  font-weight: 600;
  font-size: 1.05rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--lumen-text);
}

.lumen-process__description {
  margin-top: 0.5rem;
  font-size: 0.9rem;
  line-height: 1.65;
  color: var(--lumen-muted);
}
</style>
