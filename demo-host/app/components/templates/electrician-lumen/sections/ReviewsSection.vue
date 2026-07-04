<template>
  <section v-if="reviews.items.length" id="avis" class="lumen-section" aria-label="Avis clients">
    <div class="lumen-container">
      <div class="lumen-section__head" data-lumen-reveal>
        <p class="lumen-kicker">Avis</p>
        <h2 class="lumen-heading">{{ reviews.heading }}</h2>
      </div>

      <ul class="lumen-reviews__grid">
        <li
          v-for="(review, index) in reviews.items.slice(0, 6)"
          :key="`${review.author}-${index}`"
          class="lumen-reviews__card"
          data-lumen-reveal
          :style="{ '--lumen-reveal-delay': `${(index % 3) * 100}ms` }"
        >
          <p class="lumen-reviews__stars" :aria-label="`Note : ${review.rating} sur 5`">
            <svg v-for="star in 5" :key="star" viewBox="0 0 20 20" class="lumen-reviews__star" :class="{ 'is-dim': star > review.rating }" aria-hidden="true">
              <path d="M10 1.7l2.5 5.2 5.7.7-4.2 3.9 1.1 5.6L10 14.4l-5.1 2.7 1.1-5.6L1.8 7.6l5.7-.7L10 1.7z" fill="currentColor" />
            </svg>
          </p>
          <blockquote class="lumen-reviews__quote">{{ review.quote }}</blockquote>
          <p class="lumen-reviews__author">— {{ review.author }}</p>
        </li>
      </ul>

      <p class="lumen-reviews__source" data-lumen-reveal>Avis publiés sur Google</p>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Avis clients réels, injectés par l'enrichissement (avis Google).
 * Section masquée tant qu'aucun avis réel n'existe — jamais de faux avis.
 */
import type { LumenReviewsContent } from '../types'

defineProps<{
  reviews: LumenReviewsContent
}>()
</script>

<style scoped>
.lumen-reviews__grid {
  margin-top: 2.8rem;
  display: grid;
  gap: 1.1rem;
  list-style: none;
  padding: 0;
}

@media (min-width: 768px) {
  .lumen-reviews__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .lumen-reviews__grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.lumen-reviews__card {
  display: flex;
  flex-direction: column;
  padding: 1.6rem 1.5rem;
  background: var(--lumen-panel);
  border: 1px solid var(--lumen-line);
  clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px);
}

.lumen-reviews__stars {
  display: flex;
  gap: 0.2rem;
}

.lumen-reviews__star {
  width: 15px;
  height: 15px;
  color: var(--lumen-yellow);
}

.lumen-reviews__star.is-dim {
  color: color-mix(in srgb, white 14%, transparent);
}

.lumen-reviews__quote {
  margin: 0.95rem 0 0;
  flex: 1;
  font-size: 0.93rem;
  line-height: 1.7;
  color: var(--lumen-text);
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.lumen-reviews__author {
  margin-top: 1.1rem;
  font-family: var(--lumen-font-mono);
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  color: var(--lumen-muted);
}

.lumen-reviews__source {
  margin-top: 1.6rem;
  font-family: var(--lumen-font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: color-mix(in srgb, var(--lumen-muted) 70%, transparent);
}
</style>
