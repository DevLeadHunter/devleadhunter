<template>
  <section v-if="craft.items.length" id="savoir-faire" class="cuivre-craft" aria-label="Savoir-faire">
    <div class="cuivre-container cuivre-craft__inner">
      <div class="cuivre-craft__copy" data-cuivre-reveal>
        <p class="cuivre-eyebrow"><span class="cuivre-eyebrow__num">02</span>{{ craft.kicker }}</p>
        <h2 class="cuivre-heading">{{ craft.heading }}</h2>
        <p v-if="craft.text" class="cuivre-craft__text">{{ craft.text }}</p>
      </div>

      <div class="cuivre-craft__plate" data-cuivre-reveal :style="{ '--cuivre-reveal-delay': '120ms' }">
        <p class="cuivre-craft__plate-title">
          <span class="cuivre-craft__plate-fig">Nos engagements</span>
          Les gestes du métier
        </p>

        <ol class="cuivre-craft__items">
          <li v-for="(item, index) in craft.items" :key="item.label" class="cuivre-craft__item">
            <span class="cuivre-craft__item-num" aria-hidden="true">{{ index + 1 }}</span>
            <div>
              <h3 class="cuivre-craft__item-label">{{ item.label }}</h3>
              <p class="cuivre-craft__item-description">{{ item.description }}</p>
            </div>
          </li>
        </ol>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * « Les règles de l'art » : manifeste du travail bien fait à gauche,
 * planche annotée à droite — les gestes du métier numérotés comme les
 * légendes d'une planche d'encyclopédie.
 */
import type { CuivreCraftContent } from '../types'

defineProps<{
  craft: CuivreCraftContent
}>()
</script>

<style scoped>
.cuivre-craft {
  margin-top: 5.5rem;
  padding-block: 4.2rem;
  background: var(--cuivre-tint);
  border-block: 1px solid var(--cuivre-rule);
}

.cuivre-craft__inner {
  display: grid;
  gap: 2.8rem;
  align-items: start;
}

@media (min-width: 1024px) {
  .cuivre-craft__inner {
    grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
    gap: 4.5rem;
  }
}

.cuivre-craft__text {
  margin-top: 1.2rem;
  max-width: 30rem;
  font-size: 0.97rem;
  line-height: 1.75;
  color: var(--cuivre-muted);
}

/* ---- La planche ---- */

.cuivre-craft__plate {
  background: var(--cuivre-card);
  border: 1px solid var(--cuivre-rule);
  border-radius: 18px;
  box-shadow: 0 22px 46px -32px color-mix(in srgb, var(--cuivre-blue) 55%, transparent);
  padding: clamp(1.3rem, 3vw, 2rem);
}

.cuivre-craft__plate-title {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--cuivre-rule);
  font-family: var(--cuivre-font-display);
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--cuivre-ink);
}

.cuivre-craft__plate-fig {
  display: inline-flex;
  align-items: center;
  padding: 0.22rem 0.7rem;
  border-radius: 9999px;
  background: color-mix(in srgb, var(--cuivre-aqua) 13%, white);
  font-family: var(--cuivre-font-display);
  font-weight: 700;
  font-size: 0.64rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--cuivre-blue);
}

.cuivre-craft__items {
  margin: 0;
  padding: 0.4rem 0 0;
  list-style: none;
  display: grid;
  gap: 0;
}

@media (min-width: 640px) {
  .cuivre-craft__items {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 2rem;
  }
}

.cuivre-craft__item {
  display: flex;
  gap: 0.95rem;
  padding: 1.15rem 0.2rem;
  border-bottom: 1px solid color-mix(in srgb, var(--cuivre-ink) 9%, transparent);
}

.cuivre-craft__item:last-child {
  border-bottom: none;
}

@media (min-width: 640px) {
  .cuivre-craft__item:nth-last-child(2) {
    border-bottom: none;
  }
}

.cuivre-craft__item-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  flex: none;
  background: color-mix(in srgb, var(--cuivre-blue) 10%, white);
  border: 1px solid color-mix(in srgb, var(--cuivre-blue) 45%, transparent);
  border-radius: 9999px;
  font-family: var(--cuivre-font-display);
  font-weight: 700;
  font-size: 0.88rem;
  color: var(--cuivre-blue);
}

.cuivre-craft__item-label {
  font-family: var(--cuivre-font-display);
  font-weight: 600;
  font-size: 1.06rem;
  color: var(--cuivre-ink);
}

.cuivre-craft__item-description {
  margin-top: 0.35rem;
  font-family: var(--cuivre-font-sans);
  font-size: 0.88rem;
  line-height: 1.6;
  color: var(--cuivre-muted);
}
</style>
