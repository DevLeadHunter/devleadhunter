<template>
  <section id="histoire" class="story">
    <div class="story-grid">
      <div class="story-media reveal" data-reveal>
        <div class="story-frame">
          <img :src="img(story.image as string, 900, 1100)" :alt="`L'artisan — ${businessName}`" loading="lazy" decoding="async" />
        </div>
        <div v-if="storyStats.length" class="story-stats">
          <div v-for="(s, i) in storyStats" :key="i" class="story-stat">
            <span class="story-stat-val">{{ s.value }}</span>
            <span class="story-stat-label">{{ s.label }}</span>
          </div>
        </div>
      </div>
      <div class="story-body">
        <p class="kicker">{{ story.kicker || "L'artisan" }}</p>
        <h2 class="section-title reveal" data-reveal>{{ story.heading || 'Un savoir-faire transmis, pas sous-traité' }}</h2>
        <div class="story-prose">
          <p
            v-for="(p, i) in storyParagraphs"
            :key="i"
            class="reveal"
            data-reveal
            :style="{ '--d': `${i * 70}ms` }"
          >
            {{ p }}
          </p>
        </div>
        <ul v-if="storyValues.length" class="values">
          <li
            v-for="(v, i) in storyValues"
            :key="i"
            class="value reveal"
            data-reveal
            :style="{ '--d': `${i * 70}ms` }"
          >
            <svg viewBox="0 0 24 24" class="value-ico" aria-hidden="true" v-html="icon(v.icon || 'shield')" />
            <span class="value-body">
              <span class="value-label">{{ v.label }}</span>
              <span v-if="v.description" class="value-desc">{{ v.description }}</span>
            </span>
          </li>
        </ul>
        <p v-if="story.signature_name" class="signature">
          <span class="signature-name">{{ story.signature_name }}</span>
          <span v-if="story.signature_role" class="signature-role">{{ story.signature_role }}</span>
        </p>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { StoryBlock } from '../types'
import { icon, img } from '../utils'

defineProps<{
  story: StoryBlock
  storyParagraphs: string[]
  storyValues: { label?: string; description?: string; icon?: string }[]
  storyStats: { value?: string; label?: string }[]
  businessName: string
}>()
</script>

<style scoped>
/* ════════════ Histoire ════════════ */
.story {
  padding: clamp(3.5rem, 7vw, 6rem) 0;
}
.story-grid {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 1.5rem;
  display: grid;
  grid-template-columns: 0.85fr 1fr;
  gap: clamp(2rem, 5vw, 4.5rem);
  align-items: start;
}
.story-media {
  position: sticky;
  top: 6rem;
}
.story-frame {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  aspect-ratio: 4 / 5;
  box-shadow: 0 40px 80px -44px color-mix(in srgb, var(--ink) 60%, transparent);
}
.story-frame::after {
  content: '';
  position: absolute;
  inset: 0;
  mix-blend-mode: color;
  background: color-mix(in srgb, var(--brand) 55%, transparent);
}
.story-frame img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  filter: grayscale(0.2) contrast(1.05);
}
.story-stats {
  display: flex;
  gap: 1rem;
  margin-top: 1.1rem;
}
.story-stat {
  flex: 1;
  background: var(--paper-2);
  border-radius: 13px;
  padding: 1rem;
  text-align: center;
}
.story-stat-val {
  display: block;
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700;
  font-size: 1.5rem;
  color: var(--brand);
  letter-spacing: -0.02em;
}
.story-stat-label {
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-soft);
}
.story-body .section-title {
  margin-top: 0.4rem;
}
.story-prose {
  margin-top: 1.4rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  color: var(--ink-soft);
  font-size: 1.05rem;
}
.values {
  list-style: none;
  margin-top: 2rem;
  display: grid;
  gap: 0.2rem;
}
.value {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem 0;
  border-top: 1px solid var(--hair);
}
.value:last-child {
  border-bottom: 1px solid var(--hair);
}
.value-ico {
  flex: none;
  width: 1.7rem;
  height: 1.7rem;
  color: var(--brand);
  margin-top: 0.1rem;
}
.value-label {
  display: block;
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 650;
  font-size: 1.05rem;
}
.value-desc {
  display: block;
  margin-top: 0.15rem;
  color: var(--ink-soft);
  font-size: 0.95rem;
}
.signature {
  margin-top: 2rem;
  display: flex;
  flex-direction: column;
}
.signature-name {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700;
  font-size: 1.3rem;
  color: var(--brand);
  letter-spacing: -0.01em;
}
.signature-role {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--ink-soft);
}

/* ════════════ Responsive ════════════ */
@media (max-width: 980px) {
  .story-grid {
    grid-template-columns: 1fr;
  }
  .story-media {
    position: static;
    max-width: 460px;
  }
}
</style>
