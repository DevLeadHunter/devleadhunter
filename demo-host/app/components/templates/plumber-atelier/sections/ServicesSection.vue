<template>
  <section class="services">
    <div class="section-head">
      <p class="section-kicker">Nos prestations</p>
      <h2 class="section-title reveal" data-reveal>{{ services.heading || 'Ce que nous réparons' }}</h2>
      <p v-if="services.subheading" class="section-lede reveal" data-reveal style="--d: 90ms">{{ services.subheading }}</p>
    </div>

    <ol class="svc-list">
      <li
        v-for="(item, i) in serviceItems"
        :key="i"
        class="svc-row reveal"
        data-reveal
        :style="{ '--d': `${i * 70}ms` }"
      >
        <span class="svc-num">{{ String(i + 1).padStart(2, '0') }}</span>
        <span class="svc-ico" v-html="serviceIcon(item.icon)" />
        <span class="svc-body">
          <span class="svc-name">{{ item.label }}</span>
          <span v-if="item.description" class="svc-desc">{{ item.description }}</span>
        </span>
        <svg class="svc-arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
      </li>
    </ol>
  </section>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import type { ServicesBlock } from '../types'
import { serviceIcon } from '../utils'

const props = defineProps<{
  services: ServicesBlock
}>()

const serviceItems = computed(() => {
  const items = props.services.items
  return Array.isArray(items) ? (items as Array<{ label?: string; description?: string; icon?: string }>) : []
})
</script>

<style scoped>
.services {
  padding: clamp(3.5rem, 7vw, 6rem) 0;
}
.svc-list {
  max-width: 1200px;
  margin: clamp(2rem, 4vw, 3.2rem) auto 0;
  padding: 0 1.5rem;
  list-style: none;
  border-top: 1px solid var(--hair);
}
.svc-row {
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  align-items: center;
  gap: clamp(1rem, 3vw, 2.4rem);
  padding: clamp(1.3rem, 2.5vw, 1.9rem) 0.5rem;
  border-bottom: 1px solid var(--hair);
  transition: background 0.22s ease, padding-left 0.22s ease;
}
.svc-row:hover {
  background: var(--paper-2);
  padding-left: 1.2rem;
}
.svc-num {
  font-family: 'Fraunces', serif;
  font-weight: 600;
  font-size: clamp(1.4rem, 3vw, 2.2rem);
  color: var(--paper-3);
  -webkit-text-stroke: 1px var(--ink-soft);
  font-variant-numeric: tabular-nums;
  transition: color 0.22s ease;
}
.svc-row:hover .svc-num {
  color: var(--brass);
  -webkit-text-stroke: 1px var(--brass);
}
.svc-ico :deep(svg) {
  width: 2rem;
  height: 2rem;
  color: var(--ink);
  stroke-width: 1.4;
}
.svc-name {
  display: block;
  font-family: 'Fraunces', serif;
  font-weight: 600;
  font-size: clamp(1.2rem, 2vw, 1.6rem);
  letter-spacing: -0.01em;
}
.svc-desc {
  display: block;
  margin-top: 0.25rem;
  color: var(--ink-soft);
  font-size: 0.95rem;
  max-width: 52ch;
}
.svc-arrow {
  width: 1.5rem;
  height: 1.5rem;
  color: var(--ink-soft);
  opacity: 0;
  transform: translateX(-8px);
  transition: opacity 0.22s ease, transform 0.22s ease, color 0.22s ease;
}
.svc-row:hover .svc-arrow {
  opacity: 1;
  transform: translateX(0);
  color: var(--brass);
}

/* ════════════ Responsive ════════════ */
@media (max-width: 860px) {
  .svc-row {
    grid-template-columns: auto 1fr;
    grid-template-areas: 'num ico' 'body body';
    gap: 0.8rem 1rem;
  }
  .svc-num {
    grid-area: num;
  }
  .svc-ico {
    grid-area: ico;
    justify-self: end;
  }
  .svc-body {
    grid-area: body;
  }
  .svc-arrow {
    display: none;
  }
}
</style>
