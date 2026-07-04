<template>
  <section v-if="emergency.text || emergency.items.length" id="depannage" class="lumen-emergency" aria-label="Dépannage">
    <div class="lumen-container lumen-emergency__inner">
      <div class="lumen-emergency__copy" data-lumen-reveal>
        <p class="lumen-kicker lumen-kicker--amber">Urgence & dépannage</p>
        <h2 class="lumen-heading lumen-emergency__heading">{{ emergency.heading }}</h2>
        <p v-if="emergency.text" class="lumen-emergency__text">{{ emergency.text }}</p>

        <ul v-if="emergency.items.length" class="lumen-emergency__list">
          <li v-for="item in emergency.items" :key="item" class="lumen-emergency__item">
            <span class="lumen-emergency__item-marker" aria-hidden="true">▸</span>
            {{ item }}
          </li>
        </ul>
      </div>

      <div class="lumen-emergency__panel" data-lumen-reveal :style="{ '--lumen-reveal-delay': '120ms' }">
        <template v-if="emergency.phone">
          <p class="lumen-emergency__panel-title">Un problème maintenant ?</p>
          <a :href="`tel:${emergency.phone}`" class="lumen-emergency__phone">{{ emergency.phone }}</a>
          <p v-if="emergency.availabilityLabel" class="lumen-emergency__availability">
            <span class="lumen-emergency__pulse" aria-hidden="true"></span>
            {{ emergency.availabilityLabel }}
          </p>
        </template>
        <template v-else>
          <p class="lumen-emergency__panel-title">Besoin d'un électricien ?</p>
          <a href="#contact" class="lumen-btn lumen-btn--primary">Demander un devis</a>
        </template>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Bande dépannage : rassurante plutôt qu'anxiogène — copy qui guide,
 * points concrets, et carte téléphone en évidence (liseré hasard ambre).
 */
import type { LumenEmergencyContent } from '../types'

defineProps<{
  emergency: LumenEmergencyContent
}>()
</script>

<style scoped>
.lumen-emergency {
  position: relative;
  margin-top: 5.5rem;
  background: color-mix(in srgb, var(--lumen-amber) 5%, transparent);
  border-block: 1px solid color-mix(in srgb, var(--lumen-amber) 22%, transparent);
}

/* Liserés « balisage chantier » en haut et en bas */
.lumen-emergency::before,
.lumen-emergency::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  height: 5px;
  background: repeating-linear-gradient(
    -45deg,
    color-mix(in srgb, var(--lumen-amber) 75%, transparent) 0 10px,
    transparent 10px 22px
  );
  opacity: 0.5;
}

.lumen-emergency::before {
  top: 0;
}

.lumen-emergency::after {
  bottom: 0;
}

.lumen-emergency__inner {
  display: grid;
  gap: 2.6rem;
  align-items: center;
  padding-block: 3.6rem;
}

@media (min-width: 1024px) {
  .lumen-emergency__inner {
    grid-template-columns: minmax(0, 7fr) minmax(0, 5fr);
    gap: 4rem;
  }
}

.lumen-emergency__heading {
  margin-top: 1rem;
  font-size: clamp(1.6rem, 3.4vw, 2.4rem);
}

.lumen-emergency__text {
  margin-top: 1.1rem;
  max-width: 36rem;
  line-height: 1.7;
  color: var(--lumen-muted);
}

.lumen-emergency__list {
  margin-top: 1.5rem;
  display: grid;
  gap: 0.55rem;
  list-style: none;
  padding: 0;
}

.lumen-emergency__item {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  font-size: 0.95rem;
  color: var(--lumen-text);
}

.lumen-emergency__item-marker {
  color: var(--lumen-amber);
  font-size: 0.8rem;
}

.lumen-emergency__panel {
  justify-self: stretch;
  text-align: center;
  padding: 2.2rem 1.8rem;
  background: var(--lumen-raised);
  border: 1px solid color-mix(in srgb, var(--lumen-amber) 35%, transparent);
  clip-path: polygon(14px 0, 100% 0, 100% calc(100% - 14px), calc(100% - 14px) 100%, 0 100%, 0 14px);
  box-shadow: 0 18px 60px -24px color-mix(in srgb, var(--lumen-amber) 45%, transparent);
}

.lumen-emergency__panel-title {
  font-family: var(--lumen-font-display);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-size: 0.95rem;
  color: var(--lumen-muted);
}

.lumen-emergency__phone {
  display: inline-block;
  margin-top: 0.9rem;
  font-family: var(--lumen-font-mono);
  font-weight: 600;
  font-size: clamp(1.5rem, 3.4vw, 2.1rem);
  letter-spacing: 0.02em;
  color: var(--lumen-text);
  text-decoration: none;
  transition:
    color 0.2s ease,
    text-shadow 0.2s ease;
}

.lumen-emergency__phone:hover {
  color: var(--lumen-amber);
  text-shadow: 0 0 22px color-mix(in srgb, var(--lumen-amber) 55%, transparent);
}

.lumen-emergency__availability {
  margin-top: 0.9rem;
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  font-family: var(--lumen-font-mono);
  font-size: 0.75rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--lumen-amber);
}

.lumen-emergency__pulse {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  background: var(--lumen-amber);
  box-shadow: 0 0 0 0 color-mix(in srgb, var(--lumen-amber) 55%, transparent);
  animation: lumen-pulse 2s ease-out infinite;
}

.lumen-emergency__panel .lumen-btn {
  margin-top: 1.1rem;
}

@keyframes lumen-pulse {
  0% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--lumen-amber) 55%, transparent);
  }
  70% {
    box-shadow: 0 0 0 11px transparent;
  }
  100% {
    box-shadow: 0 0 0 0 transparent;
  }
}

@media (prefers-reduced-motion: reduce) {
  .lumen-emergency__pulse {
    animation: none;
  }
}
</style>
