<template>
  <section class="reviews">
    <div class="section-head">
      <p class="kicker">Avis clients</p>
      <h2 class="section-title reveal" data-reveal>{{ testimonials.heading || 'Ce que disent nos clients' }}</h2>
    </div>
    <div class="rev-grid">
      <figure
        v-for="(t, i) in testimonialItems"
        :key="i"
        class="rev-card reveal"
        data-reveal
        :style="{ '--d': `${i * 80}ms` }"
      >
        <div class="rev-stars" :aria-label="`${t.rating || 5} sur 5`">
          <svg v-for="n in 5" :key="n" viewBox="0 0 24 24" class="star" :class="{ 'star-on': n <= (t.rating || 5) }" aria-hidden="true" v-html="icon('star')" />
        </div>
        <blockquote class="rev-quote">{{ t.quote }}</blockquote>
        <figcaption class="rev-author">
          <span class="rev-avatar" aria-hidden="true">{{ initials(t.author) }}</span>
          <span class="rev-meta">
            <span class="rev-name">{{ t.author }}</span>
            <span v-if="t.location" class="rev-loc">{{ t.location }}</span>
          </span>
        </figcaption>
      </figure>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { TestimonialsBlock } from '../types'
import { icon, initials } from '../utils'

defineProps<{
  testimonials: TestimonialsBlock
  testimonialItems: { quote?: string; author?: string; location?: string; rating?: number }[]
}>()
</script>

<style scoped>
/* ════════════ Témoignages ════════════ */
.reviews {
  background: var(--brand);
  color: #fff;
  padding: clamp(3.5rem, 7vw, 6rem) 0;
}
/* `.section-head` ajouté dans le sélecteur : préserve la victoire de spécificité de
   l'override face à la règle de base `.sig :deep(.kicker)` / `:deep(.section-title)`
   (mêmes éléments, déjà imbriqués dans `.section-head` — sortie identique). */
.reviews .section-head .kicker {
  color: color-mix(in srgb, #fff 80%, var(--signal));
}
.reviews .section-head .section-title {
  color: #fff;
}
.rev-grid {
  max-width: 1240px;
  margin: clamp(2rem, 4vw, 3rem) auto 0;
  padding: 0 1.5rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.2rem;
}
.rev-card {
  background: color-mix(in srgb, #fff 8%, transparent);
  border: 1px solid color-mix(in srgb, #fff 16%, transparent);
  border-radius: 16px;
  padding: 1.6rem 1.5rem;
  backdrop-filter: blur(2px);
}
.rev-stars {
  display: flex;
  gap: 0.15rem;
  margin-bottom: 0.9rem;
}
.rev-stars .star {
  width: 1.1rem;
  height: 1.1rem;
}
.rev-quote {
  font-size: 1.04rem;
  line-height: 1.55;
  color: color-mix(in srgb, #fff 92%, transparent);
}
.rev-author {
  margin-top: 1.3rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.rev-avatar {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--signal);
  color: #fff;
  font-weight: 700;
  font-size: 0.85rem;
  flex: none;
}
.rev-name {
  display: block;
  font-weight: 650;
}
.rev-loc {
  display: block;
  font-size: 0.82rem;
  color: color-mix(in srgb, #fff 70%, transparent);
}
</style>
