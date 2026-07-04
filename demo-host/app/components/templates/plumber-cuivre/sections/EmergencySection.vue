<template>
  <section v-if="emergency.text || emergency.items.length" id="depannage" class="cuivre-section" aria-label="Dépannage">
    <div class="cuivre-container">
      <div class="cuivre-emergency" data-cuivre-reveal>
        <svg class="cuivre-emergency__waves" viewBox="0 0 400 120" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 30 C 60 10, 120 50, 200 30 S 340 10, 400 30" />
          <path d="M0 65 C 60 45, 120 85, 200 65 S 340 45, 400 65" />
          <path d="M0 100 C 60 80, 120 120, 200 100 S 340 80, 400 100" />
        </svg>

        <div class="cuivre-emergency__copy">
          <p class="cuivre-emergency__kicker">
            <CuivreGlyph name="drop" class="cuivre-emergency__kicker-icon" />
            Urgence &amp; dépannage
          </p>
          <h2 class="cuivre-emergency__heading">{{ emergency.heading }}</h2>
          <p v-if="emergency.text" class="cuivre-emergency__text">{{ emergency.text }}</p>

          <ul v-if="emergency.items.length" class="cuivre-emergency__list">
            <li v-for="item in emergency.items" :key="item" class="cuivre-emergency__item">
              <CuivreGlyph name="check" class="cuivre-emergency__item-icon" />
              {{ item }}
            </li>
          </ul>
        </div>

        <div class="cuivre-emergency__aside">
          <template v-if="emergency.phone">
            <p class="cuivre-emergency__aside-label">Un problème maintenant ?</p>
            <a :href="`tel:${emergency.phone}`" class="cuivre-emergency__phone">{{ emergency.phone }}</a>
            <p v-if="emergency.availabilityLabel" class="cuivre-emergency__availability">
              <span class="cuivre-emergency__pulse" aria-hidden="true"></span>
              {{ emergency.availabilityLabel }}
            </p>
            <a :href="`tel:${emergency.phone}`" class="cuivre-btn cuivre-btn--blue cuivre-emergency__cta">
              <CuivreGlyph name="phone" class="cuivre-btn__icon" />
              Appeler maintenant
            </a>
          </template>
          <template v-else>
            <p class="cuivre-emergency__aside-label">Besoin d'un plombier ?</p>
            <a href="#contact" class="cuivre-btn cuivre-btn--blue cuivre-emergency__cta">Demander un devis</a>
          </template>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Carte dépannage « marine » : le seul bloc sombre de la page — carte arrondie
 * bleu nuit avec vagues en filigrane, copy rassurante qui guide (couper l'eau,
 * appeler), points turquoise et téléphone en très grand à droite.
 */
import CuivreGlyph from './CuivreGlyph.vue'
import type { CuivreEmergencyContent } from '../types'

defineProps<{
  emergency: CuivreEmergencyContent
}>()
</script>

<style scoped>
.cuivre-emergency {
  position: relative;
  display: grid;
  gap: 2.4rem;
  padding: clamp(1.9rem, 4vw, 3rem);
  background: var(--cuivre-ink);
  color: #ffffff;
  border-radius: 22px;
  overflow: hidden;
  box-shadow: 0 30px 60px -38px color-mix(in srgb, var(--cuivre-ink) 90%, transparent);
}

@media (min-width: 1024px) {
  .cuivre-emergency {
    grid-template-columns: minmax(0, 7fr) minmax(0, 5fr);
    gap: 3.5rem;
    align-items: center;
  }
}

.cuivre-emergency__waves {
  position: absolute;
  right: -4%;
  bottom: -8%;
  width: 58%;
  height: 62%;
  pointer-events: none;
}

.cuivre-emergency__waves path {
  fill: none;
  stroke: color-mix(in srgb, var(--cuivre-aqua) 30%, transparent);
  stroke-width: 2;
  stroke-linecap: round;
}

.cuivre-emergency__kicker {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.9rem;
  border-radius: 9999px;
  background: color-mix(in srgb, var(--cuivre-aqua) 16%, transparent);
  border: 1px solid color-mix(in srgb, var(--cuivre-aqua) 40%, transparent);
  font-family: var(--cuivre-font-display);
  font-weight: 700;
  font-size: 0.7rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--cuivre-blue-light);
}

.cuivre-emergency__kicker-icon {
  width: 12px;
  height: 12px;
}

.cuivre-emergency__heading {
  margin-top: 1rem;
  font-family: var(--cuivre-font-display);
  font-weight: 700;
  font-size: clamp(1.55rem, 3.2vw, 2.3rem);
  line-height: 1.15;
  letter-spacing: -0.01em;
  color: #ffffff;
  text-wrap: balance;
}

.cuivre-emergency__text {
  margin-top: 1rem;
  max-width: 34rem;
  font-size: 0.96rem;
  line-height: 1.7;
  color: color-mix(in srgb, white 78%, transparent);
}

.cuivre-emergency__list {
  margin-top: 1.4rem;
  display: grid;
  gap: 0.55rem;
  list-style: none;
  padding: 0;
}

.cuivre-emergency__item {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  font-size: 0.93rem;
  color: #ffffff;
}

.cuivre-emergency__item-icon {
  width: 13px;
  height: 13px;
  flex: none;
  transform: translateY(1px);
  color: var(--cuivre-aqua);
}

.cuivre-emergency__aside {
  position: relative;
  text-align: center;
  padding: 1.6rem 1.2rem;
  background: color-mix(in srgb, white 6%, transparent);
  border: 1px solid color-mix(in srgb, white 14%, transparent);
  border-radius: 16px;
}

.cuivre-emergency__aside-label {
  font-family: var(--cuivre-font-display);
  font-weight: 600;
  font-size: 1rem;
  color: color-mix(in srgb, white 85%, transparent);
}

.cuivre-emergency__phone {
  display: inline-block;
  margin-top: 0.7rem;
  font-family: var(--cuivre-font-display);
  font-weight: 800;
  font-size: clamp(1.7rem, 3.6vw, 2.3rem);
  letter-spacing: 0.01em;
  color: #ffffff;
  text-decoration: none;
  transition: color 0.2s ease;
}

.cuivre-emergency__phone:hover {
  color: var(--cuivre-blue-light);
}

.cuivre-emergency__availability {
  margin-top: 0.6rem;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--cuivre-font-sans);
  font-weight: 600;
  font-size: 0.74rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--cuivre-blue-light);
}

.cuivre-emergency__pulse {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  background: var(--cuivre-aqua);
  box-shadow: 0 0 0 0 color-mix(in srgb, var(--cuivre-aqua) 55%, transparent);
  animation: cuivre-pulse 2s ease-out infinite;
}

.cuivre-emergency__cta {
  margin-top: 1.2rem;
}

@keyframes cuivre-pulse {
  0% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--cuivre-aqua) 55%, transparent);
  }
  70% {
    box-shadow: 0 0 0 11px transparent;
  }
  100% {
    box-shadow: 0 0 0 0 transparent;
  }
}

@media (prefers-reduced-motion: reduce) {
  .cuivre-emergency__pulse {
    animation: none;
  }
}
</style>
