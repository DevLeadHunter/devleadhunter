<template>
  <section class="artisan">
    <div class="artisan-grid">
      <div class="artisan-frame reveal" data-reveal>
        <div class="frame-corner frame-corner-tl"></div>
        <div class="frame-corner frame-corner-br"></div>
        <svg class="frame-mark" viewBox="0 0 64 64" aria-hidden="true">
          <path d="M16 44V28a8 8 0 0 1 8-8h6m0 0-5-5m5 5-5 5M34 20h6a8 8 0 0 1 8 8v16" />
          <circle cx="16" cy="48" r="4" />
          <circle cx="48" cy="48" r="4" />
        </svg>
        <p class="frame-cap">Atelier · {{ city || 'votre région' }}</p>
      </div>
      <div class="artisan-body">
        <h2 class="section-title reveal" data-reveal>{{ whyUs.heading || 'Un artisan, pas un standard téléphonique' }}</h2>
        <ul class="guarantees">
          <li
            v-for="(item, i) in whyItems"
            :key="i"
            class="guarantee reveal"
            data-reveal
            :style="{ '--d': `${i * 70}ms` }"
          >
            <svg class="guarantee-tick" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 13 4 4L19 7" /></svg>
            <span>{{ item.label }}</span>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import type { WhyUsBlock } from '../types'

const props = defineProps<{
  whyUs: WhyUsBlock
  city: string
}>()

const whyItems = computed(() => {
  const items = props.whyUs.items
  return Array.isArray(items) ? (items as Array<{ label?: string }>) : []
})
</script>

<style scoped>
.artisan {
  padding: clamp(3rem, 6vw, 5.5rem) 0;
  background: var(--paper-2);
  border-top: 1px solid var(--hair);
  border-bottom: 1px solid var(--hair);
}
.artisan-grid {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
  display: grid;
  grid-template-columns: 5fr 7fr;
  gap: clamp(2rem, 5vw, 4rem);
  align-items: center;
}
.artisan-frame {
  position: relative;
  aspect-ratio: 4 / 5;
  background: var(--paper-3);
  border: 1px solid var(--hair);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1.2rem;
}
.frame-corner {
  position: absolute;
  width: 18px;
  height: 18px;
  border: 1.5px solid var(--brass);
}
.frame-corner-tl {
  top: 12px;
  left: 12px;
  border-right: 0;
  border-bottom: 0;
}
.frame-corner-br {
  bottom: 12px;
  right: 12px;
  border-left: 0;
  border-top: 0;
}
.frame-mark {
  width: 38%;
  height: auto;
  color: var(--ink);
  opacity: 0.5;
  stroke-width: 1.4;
}
.frame-cap {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--ink-soft);
}
.guarantees {
  list-style: none;
  margin-top: 2rem;
  display: flex;
  flex-direction: column;
}
.guarantee {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 0;
  border-top: 1px solid var(--hair);
  font-size: 1.05rem;
}
.guarantee:last-child {
  border-bottom: 1px solid var(--hair);
}
.guarantee-tick {
  flex: none;
  width: 1.4rem;
  height: 1.4rem;
  color: var(--brass);
  stroke-width: 2;
}

/* ════════════ Responsive ════════════ */
@media (max-width: 860px) {
  .artisan-grid {
    grid-template-columns: 1fr;
  }
}
</style>
