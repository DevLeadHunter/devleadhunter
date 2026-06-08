<template>
  <section id="realisations" class="gallery">
    <div class="section-head">
      <p class="kicker">Réalisations</p>
      <h2 class="section-title reveal" data-reveal>{{ gallery.heading || 'Quelques chantiers récents' }}</h2>
      <p v-if="gallery.subheading" class="section-lede reveal" data-reveal style="--d: 80ms">
        {{ gallery.subheading }}
      </p>
    </div>
    <div class="gal-grid">
      <figure
        v-for="(g, i) in galleryItems"
        :key="i"
        class="gal-item reveal"
        :class="`gal-item--${i % 6}`"
        data-reveal
        :style="{ '--d': `${i * 60}ms` }"
      >
        <img :src="img(g.image, 900, 1100)" :alt="g.caption || 'Chantier réalisé'" loading="lazy" decoding="async" />
        <figcaption>
          <span v-if="g.location" class="gal-loc">{{ g.location }}</span>
          <span class="gal-cap">{{ g.caption }}</span>
        </figcaption>
      </figure>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { GalleryBlock } from '../types'
import { img } from '../utils'

defineProps<{
  gallery: GalleryBlock
  galleryItems: { image?: string; caption?: string; location?: string }[]
}>()
</script>

<style scoped>
/* ════════════ Galerie ════════════ */
.gallery {
  padding: clamp(3.5rem, 7vw, 6rem) 0;
}
.gal-grid {
  max-width: 1240px;
  margin: clamp(2rem, 4vw, 3rem) auto 0;
  padding: 0 1.5rem;
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  grid-auto-rows: 200px;
  grid-auto-flow: dense;
  gap: 1rem;
}
.gal-item {
  position: relative;
  overflow: hidden;
  border-radius: 16px;
  grid-column: span 2;
  grid-row: span 1;
}
.gal-item--0 {
  grid-column: span 3;
  grid-row: span 2;
}
.gal-item--3 {
  grid-column: span 3;
  grid-row: span 2;
}
.gal-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.5s cubic-bezier(0.22, 1, 0.36, 1);
}
.gal-item:hover img {
  transform: scale(1.05);
}
.gal-item figcaption {
  position: absolute;
  inset: auto 0 0 0;
  padding: 1.4rem 1.1rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  color: #fff;
  background: linear-gradient(to top, color-mix(in srgb, var(--ink) 88%, transparent), transparent);
  transform: translateY(8px);
  opacity: 0;
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.gal-item:hover figcaption {
  opacity: 1;
  transform: translateY(0);
}
.gal-loc {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: color-mix(in srgb, #fff 78%, var(--signal));
}
.gal-cap {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 600;
  font-size: 1.02rem;
}

/* ════════════ Responsive ════════════ */
@media (max-width: 980px) {
  .gal-grid {
    grid-template-columns: repeat(2, 1fr);
    grid-auto-rows: 180px;
  }
  .gal-item,
  .gal-item--0,
  .gal-item--3 {
    grid-column: span 1;
    grid-row: span 1;
  }
  .gal-item figcaption {
    opacity: 1;
    transform: none;
  }
}

@media (max-width: 680px) {
  .gal-grid {
    grid-template-columns: 1fr;
  }
}
</style>
