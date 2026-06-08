<template>
  <section id="services" class="services">
    <div class="section-head">
      <p class="kicker">Nos prestations</p>
      <h2 class="section-title reveal" data-reveal>{{ services.heading || 'Ce que nous prenons en charge' }}</h2>
      <p v-if="services.subheading" class="section-lede reveal" data-reveal style="--d: 80ms">
        {{ services.subheading }}
      </p>
    </div>
    <div class="svc-grid">
      <article
        v-for="(s, i) in serviceItems"
        :key="i"
        class="svc-card reveal"
        data-reveal
        :style="{ '--d': `${i * 60}ms` }"
      >
        <span class="svc-ico"><svg viewBox="0 0 24 24" aria-hidden="true" v-html="icon(s.icon || 'pipe')" /></span>
        <h3 class="svc-name">{{ s.label }}</h3>
        <p v-if="s.description" class="svc-desc">{{ s.description }}</p>
        <span class="svc-corner" aria-hidden="true"></span>
      </article>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { ServicesBlock } from '../types'
import { icon } from '../utils'

defineProps<{
  services: ServicesBlock
  serviceItems: { label?: string; description?: string; icon?: string }[]
}>()
</script>

<style scoped>
/* ════════════ Services ════════════ */
.services {
  padding: clamp(3rem, 6vw, 5rem) 0;
}
.svc-grid {
  max-width: 1240px;
  margin: clamp(2rem, 4vw, 3rem) auto 0;
  padding: 0 1.5rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.1rem;
}
.svc-card {
  position: relative;
  background: var(--paper);
  border: 1px solid var(--hair);
  border-radius: 16px;
  padding: 1.6rem 1.5rem 1.7rem;
  overflow: hidden;
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
}
.svc-card:hover {
  transform: translateY(-4px);
  border-color: color-mix(in srgb, var(--brand) 40%, var(--hair));
  box-shadow: 0 24px 44px -28px color-mix(in srgb, var(--ink) 55%, transparent);
}
.svc-ico {
  display: inline-grid;
  place-items: center;
  width: 3rem;
  height: 3rem;
  border-radius: 12px;
  background: var(--brand-soft);
  color: var(--brand);
  margin-bottom: 1.1rem;
}
.svc-ico :deep(svg) {
  width: 1.55rem;
  height: 1.55rem;
}
.svc-name {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 650;
  font-size: 1.2rem;
  letter-spacing: -0.01em;
}
.svc-desc {
  margin-top: 0.5rem;
  color: var(--ink-soft);
  font-size: 0.96rem;
}
.svc-corner {
  position: absolute;
  top: 0;
  right: 0;
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 0 26px 26px 0;
  border-color: transparent var(--signal) transparent transparent;
  opacity: 0;
  transition: opacity 0.22s ease;
}
.svc-card:hover .svc-corner {
  opacity: 1;
}
</style>
