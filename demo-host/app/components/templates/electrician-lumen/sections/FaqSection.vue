<template>
  <section v-if="faq.items.length" id="faq" class="lumen-section" aria-label="Questions fréquentes">
    <div class="lumen-container lumen-faq__container">
      <div class="lumen-section__head" data-lumen-reveal>
        <p class="lumen-kicker">FAQ</p>
        <h2 class="lumen-heading">{{ faq.heading }}</h2>
      </div>

      <div class="lumen-faq__list" data-lumen-reveal :style="{ '--lumen-reveal-delay': '110ms' }">
        <details v-for="item in faq.items" :key="item.question" class="lumen-faq__item">
          <summary class="lumen-faq__question">
            {{ item.question }}
            <span class="lumen-faq__toggle" aria-hidden="true">+</span>
          </summary>
          <p class="lumen-faq__answer">{{ item.answer }}</p>
        </details>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * FAQ en accordéons natifs (details/summary) : accessible clavier,
 * zéro JS, toggle « + » qui pivote à l'ouverture.
 */
import type { LumenFaqContent } from '../types'

defineProps<{
  faq: LumenFaqContent
}>()
</script>

<style scoped>
.lumen-faq__container {
  max-width: 50rem;
}

.lumen-faq__list {
  margin-top: 2.4rem;
  border-top: 1px solid var(--lumen-line);
}

.lumen-faq__item {
  border-bottom: 1px solid var(--lumen-line);
}

.lumen-faq__question {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.4rem;
  padding: 1.25rem 0.2rem;
  font-family: var(--lumen-font-body);
  font-weight: 500;
  font-size: 1rem;
  color: var(--lumen-text);
  cursor: pointer;
  list-style: none;
  transition: color 0.2s ease;
}

.lumen-faq__question::-webkit-details-marker {
  display: none;
}

.lumen-faq__question:hover {
  color: var(--lumen-yellow);
}

.lumen-faq__toggle {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  font-family: var(--lumen-font-mono);
  font-size: 1.05rem;
  color: var(--lumen-yellow);
  border: 1px solid color-mix(in srgb, var(--lumen-yellow) 35%, transparent);
  clip-path: polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px);
  transition: transform 0.25s ease, background-color 0.25s ease;
}

.lumen-faq__item[open] .lumen-faq__toggle {
  transform: rotate(45deg);
  background: color-mix(in srgb, var(--lumen-yellow) 12%, transparent);
}

.lumen-faq__answer {
  margin: 0;
  padding: 0 0.2rem 1.4rem;
  max-width: 42rem;
  font-size: 0.93rem;
  line-height: 1.7;
  color: var(--lumen-muted);
}

@media (prefers-reduced-motion: reduce) {
  .lumen-faq__toggle {
    transition: none;
  }
}
</style>
