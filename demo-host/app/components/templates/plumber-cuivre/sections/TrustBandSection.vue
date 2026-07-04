<template>
  <section v-if="items.length" class="cuivre-trust" aria-label="Garanties">
    <div class="cuivre-container">
      <dl class="cuivre-trust__grid">
        <div v-for="(item, index) in items" :key="`${item.value}-${index}`" class="cuivre-trust__cell" data-cuivre-reveal :style="{ '--cuivre-reveal-delay': `${index * 80}ms` }">
          <dd class="cuivre-trust__value">{{ item.value }}</dd>
          <dt class="cuivre-trust__label">{{ item.label }}</dt>
        </div>
      </dl>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Bande de confiance façon « fiche technique » imprimée : 4 repères entre
 * doubles filets (dépannage 7j/7, décennale, devis 0 €, note Google enrichie),
 * valeurs en grande serif, libellés en petites capitales.
 */
import type { CuivreTrustItem } from '../types'

defineProps<{
  items: CuivreTrustItem[]
}>()
</script>

<style scoped>
.cuivre-trust {
  border-block: 1px solid var(--cuivre-rule);
  background: var(--cuivre-tint);
}

.cuivre-trust__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 0;
}

@media (min-width: 768px) {
  .cuivre-trust__grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.cuivre-trust__cell {
  position: relative;
  padding: 1.5rem 1.3rem;
  display: flex;
  flex-direction: column;
}

.cuivre-trust__cell::before {
  content: '';
  position: absolute;
  left: 0;
  top: 1.4rem;
  bottom: 1.4rem;
  width: 1px;
  background: var(--cuivre-rule);
}

.cuivre-trust__cell:first-child::before {
  display: none;
}

@media (max-width: 767px) {
  .cuivre-trust__cell:nth-child(odd)::before {
    display: none;
  }
}

.cuivre-trust__value {
  margin: 0;
  order: 1;
  font-family: var(--cuivre-font-display);
  font-weight: 700;
  font-size: clamp(1.35rem, 2.6vw, 1.8rem);
  line-height: 1.1;
  color: var(--cuivre-ink);
}

.cuivre-trust__label {
  order: 2;
  margin-top: 0.4rem;
  font-family: var(--cuivre-font-sans);
  font-weight: 500;
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--cuivre-muted);
}
</style>
