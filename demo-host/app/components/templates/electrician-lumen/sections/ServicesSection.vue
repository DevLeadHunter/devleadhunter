<template>
  <section v-if="services.items.length" id="services" class="lumen-section" aria-label="Services">
    <div class="lumen-container">
      <div class="lumen-section__head" data-lumen-reveal>
        <p class="lumen-kicker">Services</p>
        <h2 class="lumen-heading">{{ services.heading }}</h2>
        <p v-if="services.subheading" class="lumen-section__subheading">{{ services.subheading }}</p>
      </div>

      <ul class="lumen-services__grid">
        <li
          v-for="(item, index) in services.items"
          :key="item.label"
          class="lumen-services__card"
          data-lumen-reveal
          :style="{ '--lumen-reveal-delay': `${(index % 3) * 90}ms` }"
        >
          <span class="lumen-services__icon-plate" aria-hidden="true">
            <LumenIcon :name="item.icon" class="lumen-services__icon" />
          </span>
          <h3 class="lumen-services__label">{{ item.label }}</h3>
          <p class="lumen-services__description">{{ item.description }}</p>
          <span class="lumen-services__index" aria-hidden="true">{{ String(index + 1).padStart(2, '0') }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Grille des services : cartes chanfreinées « plaques d'équipement »,
 * icônes filaires custom, index mono en filigrane.
 */
import LumenIcon from './LumenIcon.vue'
import type { LumenServicesContent } from '../types'

defineProps<{
  services: LumenServicesContent
}>()
</script>

<style scoped>
.lumen-services__grid {
  margin-top: 2.8rem;
  display: grid;
  gap: 1.1rem;
  list-style: none;
  padding: 0;
}

@media (min-width: 640px) {
  .lumen-services__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .lumen-services__grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.lumen-services__card {
  position: relative;
  padding: 1.7rem 1.6rem 1.9rem;
  background: var(--lumen-panel);
  border: 1px solid var(--lumen-line);
  clip-path: polygon(14px 0, 100% 0, 100% calc(100% - 14px), calc(100% - 14px) 100%, 0 100%, 0 14px);
  transition:
    border-color 0.22s ease,
    transform 0.22s ease,
    background-color 0.22s ease;
}

.lumen-services__card:hover {
  border-color: color-mix(in srgb, var(--lumen-yellow) 45%, transparent);
  background: color-mix(in srgb, var(--lumen-yellow) 3%, var(--lumen-panel));
  transform: translateY(-4px);
}

.lumen-services__icon-plate {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  background: var(--lumen-raised);
  border: 1px solid var(--lumen-line);
  clip-path: polygon(9px 0, 100% 0, 100% calc(100% - 9px), calc(100% - 9px) 100%, 0 100%, 0 9px);
  transition: box-shadow 0.22s ease;
}

.lumen-services__card:hover .lumen-services__icon-plate {
  box-shadow: 0 0 22px -4px color-mix(in srgb, var(--lumen-yellow) 55%, transparent);
}

.lumen-services__icon {
  width: 23px;
  height: 23px;
  color: var(--lumen-yellow);
}

.lumen-services__label {
  margin-top: 1.15rem;
  font-family: var(--lumen-font-display);
  font-weight: 600;
  font-size: 1.02rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--lumen-text);
}

.lumen-services__description {
  margin-top: 0.55rem;
  font-size: 0.9rem;
  line-height: 1.65;
  color: var(--lumen-muted);
}

.lumen-services__index {
  position: absolute;
  top: 1.15rem;
  right: 1.2rem;
  font-family: var(--lumen-font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  color: color-mix(in srgb, white 22%, transparent);
}
</style>
