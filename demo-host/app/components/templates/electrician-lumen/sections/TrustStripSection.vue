<template>
  <section v-if="items.length" class="lumen-trust" aria-label="Garanties">
    <div class="lumen-container">
      <dl class="lumen-trust__grid">
        <div v-for="(item, index) in items" :key="`${item.value}-${index}`" class="lumen-trust__cell" data-lumen-reveal :style="{ '--lumen-reveal-delay': `${index * 90}ms` }">
          <dt class="lumen-trust__label">{{ item.label }}</dt>
          <dd class="lumen-trust__value">{{ item.value }}</dd>
        </div>
      </dl>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Bandeau de confiance : 4 repères (dépannage 7j/7, normes, garantie, note Google
 * injectée par l'enrichissement) affichés en « instruments de mesure » mono.
 */
import type { LumenTrustItem } from '../types'

defineProps<{
  items: LumenTrustItem[]
}>()
</script>

<style scoped>
.lumen-trust {
  border-block: 1px solid var(--lumen-line);
  background: linear-gradient(180deg, color-mix(in srgb, white 3%, transparent), transparent);
}

.lumen-trust__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 0;
}

@media (min-width: 768px) {
  .lumen-trust__grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.lumen-trust__cell {
  position: relative;
  padding: 1.6rem 1.4rem;
}

.lumen-trust__cell::before {
  content: '';
  position: absolute;
  left: 0;
  top: 1.7rem;
  bottom: 1.7rem;
  width: 1px;
  background: var(--lumen-line);
}

.lumen-trust__cell:first-child::before {
  display: none;
}

@media (max-width: 767px) {
  .lumen-trust__cell:nth-child(odd)::before {
    display: none;
  }
}

.lumen-trust__value {
  margin: 0.35rem 0 0;
  font-family: var(--lumen-font-mono);
  font-weight: 600;
  font-size: clamp(1.15rem, 2.2vw, 1.45rem);
  color: var(--lumen-text);
}

.lumen-trust__label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--lumen-font-mono);
  font-size: 0.7rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--lumen-muted);
}

.lumen-trust__label::before {
  content: '';
  width: 6px;
  height: 6px;
  flex: none;
  background: var(--lumen-yellow);
  box-shadow: 0 0 8px color-mix(in srgb, var(--lumen-yellow) 70%, transparent);
}
</style>
