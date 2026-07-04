<template>
  <section v-if="process.items.length" id="methode" class="cuivre-section" aria-label="Méthode">
    <div class="cuivre-container">
      <div class="cuivre-section__head" data-cuivre-reveal>
        <p class="cuivre-eyebrow"><span class="cuivre-eyebrow__num">04</span>Méthode</p>
        <h2 class="cuivre-heading">{{ process.heading }}</h2>
        <p v-if="process.subheading" class="cuivre-section__subheading">{{ process.subheading }}</p>
      </div>

      <ol class="cuivre-process__list">
        <li
          v-for="(step, index) in process.items"
          :key="step.title"
          class="cuivre-process__step"
          data-cuivre-reveal
          :style="{ '--cuivre-reveal-delay': `${index * 110}ms` }"
        >
          <div class="cuivre-process__rail" aria-hidden="true">
            <span class="cuivre-process__node"></span>
            <span v-if="index < process.items.length - 1" class="cuivre-process__wire"></span>
          </div>
          <div class="cuivre-process__content">
            <p class="cuivre-process__step-label">Étape {{ String(index + 1).padStart(2, '0') }}</p>
            <h3 class="cuivre-process__title">{{ step.title }}</h3>
            <p class="cuivre-process__description">{{ step.description }}</p>
          </div>
        </li>
      </ol>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Méthode en timeline verticale : un rail cuivre relie des nœuds-raccords,
 * chaque étape (appel → visite & devis → intervention → contrôle) se révèle
 * en descendant le long du tuyau.
 */
import type { CuivreProcessContent } from '../types'

defineProps<{
  process: CuivreProcessContent
}>()
</script>

<style scoped>
.cuivre-process__list {
  margin: 2.8rem 0 0;
  padding: 0;
  list-style: none;
  max-width: 44rem;
}

.cuivre-process__step {
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr);
  column-gap: 1.4rem;
}

.cuivre-process__rail {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.cuivre-process__node {
  width: 15px;
  height: 15px;
  flex: none;
  margin-top: 0.4rem;
  border: 2px solid var(--cuivre-blue);
  border-radius: 9999px;
  background: var(--cuivre-card);
  box-shadow: inset 0 0 0 2.5px var(--cuivre-card), inset 0 0 0 6px color-mix(in srgb, var(--cuivre-blue) 35%, transparent);
}

.cuivre-process__wire {
  flex: 1;
  width: 2px;
  margin-block: 0.35rem;
  background: linear-gradient(180deg, var(--cuivre-blue), color-mix(in srgb, var(--cuivre-blue) 45%, var(--cuivre-card)));
  border-radius: 1px;
}

.cuivre-process__content {
  padding-bottom: 2.3rem;
}

.cuivre-process__step:last-child .cuivre-process__content {
  padding-bottom: 0.4rem;
}

.cuivre-process__step-label {
  font-family: var(--cuivre-font-sans);
  font-weight: 600;
  font-size: 0.68rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--cuivre-blue);
}

.cuivre-process__title {
  margin-top: 0.4rem;
  font-family: var(--cuivre-font-display);
  font-weight: 600;
  font-size: 1.3rem;
  color: var(--cuivre-ink);
}

.cuivre-process__description {
  margin-top: 0.45rem;
  max-width: 32rem;
  font-family: var(--cuivre-font-sans);
  font-size: 0.93rem;
  line-height: 1.65;
  color: var(--cuivre-muted);
}
</style>
