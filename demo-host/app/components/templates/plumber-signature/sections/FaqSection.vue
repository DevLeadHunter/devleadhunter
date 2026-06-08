<template>
  <section id="faq" class="faq">
    <div class="section-head">
      <p class="kicker">Questions fréquentes</p>
      <h2 class="section-title reveal" data-reveal>{{ faq.heading || 'Vous vous demandez peut-être…' }}</h2>
    </div>
    <div class="faq-list">
      <div
        v-for="(f, i) in faqItems"
        :key="i"
        class="faq-item reveal"
        :class="{ open: openFaq === i }"
        data-reveal
        :style="{ '--d': `${i * 50}ms` }"
      >
        <button
          class="faq-q"
          :aria-expanded="openFaq === i"
          :aria-controls="`faq-a-${i}`"
          @click="toggleFaq(i)"
        >
          <span>{{ f.question }}</span>
          <svg viewBox="0 0 24 24" class="faq-chevron" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
        </button>
        <div :id="`faq-a-${i}`" class="faq-a" role="region">
          <p>{{ f.answer }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { FaqBlock } from '../types'

defineProps<{
  faq: FaqBlock
  faqItems: { question?: string; answer?: string }[]
}>()

/* ── FAQ accordéon ── */
const openFaq = ref<number>(0)
function toggleFaq(i: number): void {
  openFaq.value = openFaq.value === i ? -1 : i
}
</script>

<style scoped>
/* ════════════ FAQ ════════════ */
.faq {
  padding: clamp(3.5rem, 7vw, 6rem) 0;
}
.faq-list {
  max-width: 820px;
  margin: clamp(2rem, 4vw, 2.8rem) auto 0;
  padding: 0 1.5rem;
}
.faq-item {
  border-bottom: 1px solid var(--hair);
}
.faq-item:first-child {
  border-top: 1px solid var(--hair);
}
.faq-q {
  width: 100%;
  background: none;
  border: 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.3rem 0.25rem;
  text-align: left;
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 600;
  font-size: 1.1rem;
  letter-spacing: -0.01em;
  color: var(--ink);
}
.faq-chevron {
  width: 1.3rem;
  height: 1.3rem;
  flex: none;
  color: var(--signal);
  transition: transform 0.28s ease;
}
.faq-item.open .faq-chevron {
  transform: rotate(180deg);
}
.faq-a {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.32s cubic-bezier(0.22, 1, 0.36, 1);
}
.faq-item.open .faq-a {
  grid-template-rows: 1fr;
}
.faq-a > p {
  overflow: hidden;
  margin: 0;
  color: var(--ink-soft);
  font-size: 1rem;
  line-height: 1.6;
  padding-bottom: 0;
  transition: padding-bottom 0.32s ease;
}
.faq-item.open .faq-a > p {
  padding-bottom: 1.3rem;
}
</style>
