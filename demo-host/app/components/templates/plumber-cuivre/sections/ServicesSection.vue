<template>
  <section v-if="services.items.length" id="services" class="cuivre-section" aria-label="Services">
    <div class="cuivre-container">
      <div class="cuivre-section__head" data-cuivre-reveal>
        <p class="cuivre-eyebrow"><span class="cuivre-eyebrow__num">01</span>Services</p>
        <h2 class="cuivre-heading">{{ services.heading }}</h2>
        <p v-if="services.subheading" class="cuivre-section__subheading">{{ services.subheading }}</p>
      </div>

      <ol class="cuivre-services__list">
        <li
          v-for="(item, index) in services.items"
          :key="item.label"
          class="cuivre-services__row"
          data-cuivre-reveal
          :style="{ '--cuivre-reveal-delay': `${Math.min(index, 3) * 70}ms` }"
        >
          <span class="cuivre-services__num" aria-hidden="true">{{ String(index + 1).padStart(2, '0') }}.</span>
          <h3 class="cuivre-services__label">{{ item.label }}</h3>
          <p class="cuivre-services__description">{{ item.description }}</p>
        </li>
      </ol>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Services en « table des matières » éditoriale : lignes numérotées en serif
 * italique cuivre, séparées par des filets — l'inverse d'une grille de cartes.
 */
import type { CuivreServicesContent } from '../types'

defineProps<{
  services: CuivreServicesContent
}>()
</script>

<style scoped>
.cuivre-services__list {
  margin: 2.6rem 0 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--cuivre-rule);
}

.cuivre-services__row {
  display: grid;
  grid-template-columns: 3.2rem minmax(0, 1fr);
  grid-template-areas:
    'num label'
    'num description';
  column-gap: 0.6rem;
  padding: 1.35rem 0.4rem;
  border-bottom: 1px solid var(--cuivre-rule);
  transition: background-color 0.25s ease;
}

@media (min-width: 900px) {
  .cuivre-services__row {
    grid-template-columns: 4.2rem minmax(0, 5fr) minmax(0, 6fr);
    grid-template-areas: 'num label description';
    align-items: baseline;
    column-gap: 1.6rem;
    padding: 1.55rem 0.6rem;
  }
}

.cuivre-services__row:hover {
  background: var(--cuivre-tint);
  border-radius: 12px;
}

.cuivre-services__num {
  grid-area: num;
  font-family: var(--cuivre-font-display);
  font-weight: 700;
  font-size: 1.05rem;
  color: var(--cuivre-blue);
}

.cuivre-services__label {
  grid-area: label;
  font-family: var(--cuivre-font-display);
  font-weight: 600;
  font-size: clamp(1.15rem, 2vw, 1.4rem);
  line-height: 1.25;
  color: var(--cuivre-ink);
  transition: color 0.25s ease;
}

.cuivre-services__row:hover .cuivre-services__label {
  color: var(--cuivre-blue);
}

.cuivre-services__description {
  grid-area: description;
  margin-top: 0.35rem;
  font-family: var(--cuivre-font-sans);
  font-size: 0.92rem;
  line-height: 1.65;
  color: var(--cuivre-muted);
}

@media (min-width: 900px) {
  .cuivre-services__description {
    margin-top: 0;
  }
}
</style>
