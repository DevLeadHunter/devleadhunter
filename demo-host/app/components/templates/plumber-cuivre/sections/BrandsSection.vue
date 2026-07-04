<template>
  <section v-if="brands.items.length" class="cuivre-brands" aria-label="Marques posées">
    <div class="cuivre-container cuivre-brands__inner" data-cuivre-reveal>
      <div class="cuivre-brands__copy">
        <h2 class="cuivre-brands__heading">{{ brands.heading }}</h2>
        <p v-if="brands.subheading" class="cuivre-brands__subheading">{{ brands.subheading }}</p>
      </div>

      <ul class="cuivre-brands__list">
        <li v-for="brand in brands.items" :key="brand" class="cuivre-brands__chip">{{ brand }}</li>
      </ul>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Bande « marques posées » : les fabricants couramment installés (Grohe,
 * Atlantic, Geberit…) en pastilles — un repère de sérieux immédiat pour le
 * visiteur, entièrement éditable dans Storyblok.
 */
import type { CuivreBrandsContent } from '../types'

defineProps<{
  brands: CuivreBrandsContent
}>()
</script>

<style scoped>
.cuivre-brands {
  margin-top: 5.5rem;
  padding-block: 3rem;
  background: var(--cuivre-tint);
  border-block: 1px solid var(--cuivre-rule);
}

.cuivre-brands__inner {
  display: grid;
  gap: 1.8rem;
  align-items: center;
}

@media (min-width: 1024px) {
  .cuivre-brands__inner {
    grid-template-columns: minmax(0, 4fr) minmax(0, 8fr);
    gap: 3rem;
  }
}

.cuivre-brands__heading {
  font-family: var(--cuivre-font-display);
  font-weight: 700;
  font-size: 1.35rem;
  letter-spacing: -0.01em;
  color: var(--cuivre-ink);
}

.cuivre-brands__subheading {
  margin-top: 0.5rem;
  font-family: var(--cuivre-font-sans);
  font-size: 0.88rem;
  line-height: 1.6;
  color: var(--cuivre-muted);
}

.cuivre-brands__list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  list-style: none;
  margin: 0;
  padding: 0;
}

.cuivre-brands__chip {
  padding: 0.55rem 1.15rem;
  border-radius: 9999px;
  background: var(--cuivre-card);
  border: 1px solid var(--cuivre-rule);
  font-family: var(--cuivre-font-display);
  font-weight: 600;
  font-size: 0.88rem;
  color: var(--cuivre-ink);
  transition: border-color 0.2s ease, color 0.2s ease;
}

.cuivre-brands__chip:hover {
  border-color: var(--cuivre-blue);
  color: var(--cuivre-blue);
}
</style>
