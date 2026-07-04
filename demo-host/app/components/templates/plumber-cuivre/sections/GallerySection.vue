<template>
  <section v-if="gallery.items.length" id="chantiers" class="cuivre-section" aria-label="Réalisations">
    <div class="cuivre-container">
      <div class="cuivre-section__head" data-cuivre-reveal>
        <p class="cuivre-eyebrow"><span class="cuivre-eyebrow__num">03</span>Réalisations</p>
        <h2 class="cuivre-heading">{{ gallery.heading }}</h2>
        <p v-if="gallery.subheading" class="cuivre-section__subheading">{{ gallery.subheading }}</p>
      </div>

      <ul class="cuivre-gallery__grid">
        <li
          v-for="(item, index) in gallery.items.slice(0, 7)"
          :key="`${item.image}-${index}`"
          class="cuivre-gallery__cell"
          :class="{ 'cuivre-gallery__cell--lead': index === 0 }"
          data-cuivre-reveal
          :style="{ '--cuivre-reveal-delay': `${(index % 3) * 80}ms` }"
        >
          <figure class="cuivre-gallery__figure">
            <img :src="item.image" :alt="item.caption || `Chantier ${index + 1}`" class="cuivre-gallery__photo" loading="lazy" />
            <figcaption class="cuivre-gallery__caption">
              <span class="cuivre-gallery__caption-dot" aria-hidden="true"></span>
              {{ item.caption || 'Chantier récent' }}
            </figcaption>
          </figure>
        </li>
      </ul>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Galerie « planches photo » façon revue imprimée : cadres papier à filets,
 * légendes italiques numérotées « Fig. N ». Remplie par l'enrichissement
 * (photos Google) et entièrement masquée quand aucune photo n'existe.
 */
import type { CuivreGalleryContent } from '../types'

defineProps<{
  gallery: CuivreGalleryContent
}>()
</script>

<style scoped>
.cuivre-gallery__grid {
  margin: 2.6rem 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.1rem;
}

@media (min-width: 1024px) {
  .cuivre-gallery__grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1.4rem;
  }
}

.cuivre-gallery__cell--lead {
  grid-column: span 2;
}

@media (min-width: 1024px) {
  .cuivre-gallery__cell--lead {
    grid-row: span 2;
  }
}

.cuivre-gallery__figure {
  margin: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 0.55rem;
  background: var(--cuivre-card);
  border: 1px solid var(--cuivre-rule);
  border-radius: 14px;
  box-shadow: 0 16px 34px -28px color-mix(in srgb, var(--cuivre-blue) 45%, transparent);
}

.cuivre-gallery__photo {
  display: block;
  width: 100%;
  flex: 1;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  border-radius: 9px;
  filter: saturate(1.02) contrast(1.02);
  transition: filter 0.3s ease;
}

.cuivre-gallery__cell--lead .cuivre-gallery__photo {
  aspect-ratio: auto;
  min-height: 100%;
}

.cuivre-gallery__figure:hover .cuivre-gallery__photo {
  filter: saturate(1.08) contrast(1.04);
}

.cuivre-gallery__caption {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.6rem 0.35rem 0.15rem;
  font-family: var(--cuivre-font-sans);
  font-size: 0.82rem;
  color: var(--cuivre-muted);
}

.cuivre-gallery__caption-dot {
  width: 7px;
  height: 7px;
  flex: none;
  border-radius: 9999px 9999px 9999px 2px;
  transform: rotate(45deg);
  background: var(--cuivre-aqua);
}
</style>
