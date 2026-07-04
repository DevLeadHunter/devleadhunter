<template>
  <section v-if="gallery.items.length" id="chantiers" class="lumen-section" aria-label="Réalisations">
    <div class="lumen-container">
      <div class="lumen-section__head" data-lumen-reveal>
        <p class="lumen-kicker">Réalisations</p>
        <h2 class="lumen-heading">{{ gallery.heading }}</h2>
        <p v-if="gallery.subheading" class="lumen-section__subheading">{{ gallery.subheading }}</p>
      </div>

      <ul class="lumen-gallery__grid">
        <li
          v-for="(item, index) in gallery.items.slice(0, 8)"
          :key="`${item.image}-${index}`"
          class="lumen-gallery__cell"
          :class="{ 'lumen-gallery__cell--wide': index === 0 }"
          data-lumen-reveal
          :style="{ '--lumen-reveal-delay': `${(index % 4) * 80}ms` }"
        >
          <img :src="item.image" :alt="item.caption || `Chantier ${index + 1}`" class="lumen-gallery__photo" loading="lazy" />
          <p v-if="item.caption" class="lumen-gallery__caption">{{ item.caption }}</p>
        </li>
      </ul>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Galerie de chantiers, remplie par l'enrichissement (photos Google).
 * Entièrement masquée quand aucune photo n'existe — jamais de placeholder gris.
 */
import type { LumenGalleryContent } from '../types'

defineProps<{
  gallery: LumenGalleryContent
}>()
</script>

<style scoped>
.lumen-gallery__grid {
  margin-top: 2.8rem;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
  list-style: none;
  padding: 0;
}

@media (min-width: 1024px) {
  .lumen-gallery__grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.lumen-gallery__cell {
  position: relative;
  border: 1px solid var(--lumen-line);
  background: var(--lumen-panel);
  padding: 0.45rem;
  clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px);
}

@media (min-width: 1024px) {
  .lumen-gallery__cell--wide {
    grid-column: span 2;
    grid-row: span 2;
  }
}

.lumen-gallery__photo {
  display: block;
  width: 100%;
  height: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  filter: saturate(0.92) contrast(1.03);
  transition: transform 0.35s ease, filter 0.35s ease;
}

.lumen-gallery__cell:hover .lumen-gallery__photo {
  transform: scale(1.025);
  filter: saturate(1) contrast(1.05);
}

.lumen-gallery__cell--wide .lumen-gallery__photo {
  aspect-ratio: auto;
  min-height: 100%;
}

.lumen-gallery__caption {
  position: absolute;
  inset-inline: 0.45rem;
  bottom: 0.45rem;
  margin: 0;
  padding: 1.6rem 0.8rem 0.6rem;
  font-family: var(--lumen-font-mono);
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--lumen-text);
  background: linear-gradient(180deg, transparent, color-mix(in srgb, var(--lumen-night) 88%, transparent));
}

@media (prefers-reduced-motion: reduce) {
  .lumen-gallery__photo {
    transition: none;
  }
}
</style>
