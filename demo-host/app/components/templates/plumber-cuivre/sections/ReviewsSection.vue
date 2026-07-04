<template>
  <section v-if="reviews.items.length" id="avis" class="cuivre-section" aria-label="Avis clients">
    <div class="cuivre-container">
      <div class="cuivre-section__head" data-cuivre-reveal>
        <p class="cuivre-eyebrow"><span class="cuivre-eyebrow__num">05</span>Avis</p>
        <h2 class="cuivre-heading">{{ reviews.heading }}</h2>
      </div>

      <!-- Citation vedette -->
      <blockquote v-if="featured" class="cuivre-reviews__featured" data-cuivre-reveal>
        <span class="cuivre-reviews__mark" aria-hidden="true">«</span>
        <p class="cuivre-reviews__featured-quote">{{ featured.quote }}</p>
        <footer class="cuivre-reviews__featured-footer">
          <span class="cuivre-reviews__stars" :aria-label="`Note : ${featured.rating} sur 5`">
            <CuivreGlyph v-for="star in 5" :key="star" name="star" class="cuivre-reviews__star" :class="{ 'is-empty': star > featured.rating }" />
          </span>
          <cite class="cuivre-reviews__author">{{ featured.author }}</cite>
        </footer>
      </blockquote>

      <!-- Autres avis -->
      <ul v-if="others.length" class="cuivre-reviews__grid">
        <li
          v-for="(review, index) in others"
          :key="`${review.author}-${index}`"
          class="cuivre-reviews__card"
          data-cuivre-reveal
          :style="{ '--cuivre-reveal-delay': `${(index % 2) * 90}ms` }"
        >
          <span class="cuivre-reviews__stars" :aria-label="`Note : ${review.rating} sur 5`">
            <CuivreGlyph v-for="star in 5" :key="star" name="star" class="cuivre-reviews__star" :class="{ 'is-empty': star > review.rating }" />
          </span>
          <blockquote class="cuivre-reviews__quote">{{ review.quote }}</blockquote>
          <cite class="cuivre-reviews__author">{{ review.author }}</cite>
        </li>
      </ul>

      <p class="cuivre-reviews__source" data-cuivre-reveal>Avis publiés sur Google</p>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Avis clients réels (enrichissement Google) en citations éditoriales :
 * une citation vedette en grande serif italique avec guillemet cuivre,
 * puis les autres avis en colonnes à filet. Masqué sans avis réels.
 */
import type { ComputedRef } from 'vue'
import CuivreGlyph from './CuivreGlyph.vue'
import type { CuivreReviewItem, CuivreReviewsContent } from '../types'

const props = defineProps<{
  reviews: CuivreReviewsContent
}>()

const featured: ComputedRef<CuivreReviewItem | null> = computed(
  (): CuivreReviewItem | null => props.reviews.items[0] ?? null,
)

const others: ComputedRef<CuivreReviewItem[]> = computed((): CuivreReviewItem[] => props.reviews.items.slice(1, 5))
</script>

<style scoped>
.cuivre-reviews__featured {
  position: relative;
  margin: 2.8rem auto 0;
  max-width: 46rem;
  padding-left: clamp(2.6rem, 6vw, 4rem);
}

.cuivre-reviews__mark {
  position: absolute;
  left: 0;
  top: -1.4rem;
  font-family: var(--cuivre-font-display);
  font-weight: 800;
  font-size: clamp(3.6rem, 8vw, 5.5rem);
  line-height: 1;
  color: var(--cuivre-blue);
}

.cuivre-reviews__featured-quote {
  font-family: var(--cuivre-font-display);
  font-weight: 500;
  font-size: clamp(1.25rem, 2.6vw, 1.7rem);
  line-height: 1.5;
  letter-spacing: -0.005em;
  color: var(--cuivre-ink);
}

.cuivre-reviews__featured-footer {
  margin-top: 1.2rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.cuivre-reviews__grid {
  margin: 2.6rem 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 1.8rem;
}

@media (min-width: 768px) {
  .cuivre-reviews__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 2.2rem;
  }
}

.cuivre-reviews__card {
  border-left: 2px solid var(--cuivre-blue);
  padding-left: 1.3rem;
}

.cuivre-reviews__quote {
  margin: 0.7rem 0 0;
  font-family: var(--cuivre-font-sans);
  font-size: 0.94rem;
  line-height: 1.7;
  color: var(--cuivre-ink);
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.cuivre-reviews__stars {
  display: inline-flex;
  gap: 0.18rem;
}

.cuivre-reviews__star {
  width: 13px;
  height: 13px;
  color: var(--cuivre-aqua);
}

.cuivre-reviews__star.is-empty {
  color: color-mix(in srgb, var(--cuivre-ink) 18%, transparent);
}

.cuivre-reviews__author {
  display: inline-block;
  margin-top: 0.7rem;
  font-family: var(--cuivre-font-sans);
  font-style: normal;
  font-weight: 600;
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--cuivre-muted);
}

.cuivre-reviews__featured-footer .cuivre-reviews__author {
  margin-top: 0;
}

.cuivre-reviews__source {
  margin-top: 2.2rem;
  font-family: var(--cuivre-font-sans);
  font-size: 0.82rem;
  color: var(--cuivre-muted);
}
</style>
