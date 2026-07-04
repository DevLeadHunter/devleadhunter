<template>
  <section v-if="faq.items.length" id="faq" class="cuivre-section" aria-label="Questions fréquentes">
    <div class="cuivre-container cuivre-faq__container">
      <div class="cuivre-section__head" data-cuivre-reveal>
        <p class="cuivre-eyebrow"><span class="cuivre-eyebrow__num">07</span>FAQ</p>
        <h2 class="cuivre-heading">{{ faq.heading }}</h2>
      </div>

      <div class="cuivre-faq__list" data-cuivre-reveal :style="{ '--cuivre-reveal-delay': '110ms' }">
        <details v-for="item in faq.items" :key="item.question" class="cuivre-faq__item">
          <summary class="cuivre-faq__question">
            <span class="cuivre-faq__q" aria-hidden="true">Q.</span>
            <span class="cuivre-faq__question-text">{{ item.question }}</span>
            <span class="cuivre-faq__toggle" aria-hidden="true">+</span>
          </summary>
          <p class="cuivre-faq__answer">
            <span class="cuivre-faq__r" aria-hidden="true">R.</span>
            {{ item.answer }}
          </p>
        </details>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * FAQ éditoriale « Q. / R. » en accordéons natifs (details/summary) :
 * accessible clavier, zéro JS, lettrines cuivre et filets entre questions.
 */
import type { CuivreFaqContent } from '../types'

defineProps<{
  faq: CuivreFaqContent
}>()
</script>

<style scoped>
.cuivre-faq__container {
  max-width: 50rem;
}

.cuivre-faq__list {
  margin-top: 2.4rem;
  border-top: 1px solid var(--cuivre-rule);
}

.cuivre-faq__item {
  border-bottom: 1px solid var(--cuivre-rule);
}

.cuivre-faq__question {
  display: flex;
  align-items: baseline;
  gap: 0.9rem;
  padding: 1.25rem 0.2rem;
  cursor: pointer;
  list-style: none;
  transition: color 0.2s ease;
}

.cuivre-faq__question::-webkit-details-marker {
  display: none;
}

.cuivre-faq__q,
.cuivre-faq__r {
  font-family: var(--cuivre-font-display);
  font-weight: 800;
  font-size: 1rem;
  color: var(--cuivre-blue);
  flex: none;
}

.cuivre-faq__question-text {
  flex: 1;
  font-family: var(--cuivre-font-display);
  font-weight: 600;
  font-size: 1.08rem;
  color: var(--cuivre-ink);
  transition: color 0.2s ease;
}

.cuivre-faq__question:hover .cuivre-faq__question-text {
  color: var(--cuivre-blue);
}

.cuivre-faq__toggle {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: 1px solid color-mix(in srgb, var(--cuivre-blue) 55%, transparent);
  border-radius: 9999px;
  font-family: var(--cuivre-font-sans);
  font-size: 1rem;
  color: var(--cuivre-blue);
  transition:
    transform 0.25s ease,
    background-color 0.25s ease;
}

.cuivre-faq__item[open] .cuivre-faq__toggle {
  transform: rotate(45deg);
  background: color-mix(in srgb, var(--cuivre-blue) 12%, transparent);
}

.cuivre-faq__answer {
  display: flex;
  align-items: baseline;
  gap: 0.9rem;
  margin: 0;
  padding: 0 2rem 1.4rem 0.2rem;
  font-family: var(--cuivre-font-sans);
  font-size: 0.94rem;
  line-height: 1.7;
  color: var(--cuivre-muted);
}

@media (prefers-reduced-motion: reduce) {
  .cuivre-faq__toggle {
    transition: none;
  }
}
</style>
