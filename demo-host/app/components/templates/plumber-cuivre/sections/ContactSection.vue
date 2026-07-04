<template>
  <section id="contact" class="cuivre-contact" aria-label="Contact">
    <div class="cuivre-container">
      <div class="cuivre-contact__card" data-cuivre-reveal>
        <p class="cuivre-eyebrow cuivre-contact__eyebrow"><span class="cuivre-eyebrow__num">08</span>Contact</p>
        <h2 class="cuivre-heading cuivre-contact__heading">{{ contact.heading }}</h2>
        <p v-if="contact.subheading" class="cuivre-contact__subheading">{{ contact.subheading }}</p>

        <div class="cuivre-contact__actions">
          <a v-if="contact.phone" class="cuivre-btn cuivre-btn--blue" :href="`tel:${contact.phone}`">
            <CuivreGlyph name="phone" class="cuivre-btn__icon" />
            {{ contact.ctaLabel }}
          </a>
          <a v-if="contact.email" class="cuivre-btn cuivre-btn--ghost" :href="`mailto:${contact.email}?subject=Demande de devis`">
            <CuivreGlyph name="mail" class="cuivre-btn__icon" />
            Écrire un e-mail
          </a>
        </div>

        <dl class="cuivre-contact__details">
          <div v-if="contact.phone" class="cuivre-contact__row">
            <dt class="cuivre-contact__row-label">Téléphone</dt>
            <dd class="cuivre-contact__row-value">
              <a :href="`tel:${contact.phone}`" class="cuivre-contact__link">{{ contact.phone }}</a>
            </dd>
          </div>
          <div v-if="contact.email" class="cuivre-contact__row">
            <dt class="cuivre-contact__row-label">E-mail</dt>
            <dd class="cuivre-contact__row-value">
              <a :href="`mailto:${contact.email}`" class="cuivre-contact__link">{{ contact.email }}</a>
            </dd>
          </div>
          <div v-if="contact.hours" class="cuivre-contact__row">
            <dt class="cuivre-contact__row-label">Horaires</dt>
            <dd class="cuivre-contact__row-value">{{ contact.hours }}</dd>
          </div>
          <div v-if="contact.city" class="cuivre-contact__row">
            <dt class="cuivre-contact__row-label">Secteur</dt>
            <dd class="cuivre-contact__row-value">{{ contact.city }}</dd>
          </div>
        </dl>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Contact final « carte de visite » : cartouche papier à double cadre,
 * double CTA (appel + e-mail) et fiche d'informations à filets
 * (téléphone, e-mail, horaires enrichis, secteur).
 */
import CuivreGlyph from './CuivreGlyph.vue'
import type { CuivreContactContent } from '../types'

defineProps<{
  contact: CuivreContactContent
}>()
</script>

<style scoped>
.cuivre-contact {
  padding: 5.5rem 0 6rem;
}

.cuivre-contact__card {
  position: relative;
  max-width: 46rem;
  margin-inline: auto;
  padding: clamp(2.2rem, 5vw, 3.4rem);
  text-align: center;
  background:
    radial-gradient(ellipse 75% 60% at 50% 0%, color-mix(in srgb, var(--cuivre-aqua) 8%, transparent), transparent 70%),
    var(--cuivre-card);
  border: 1px solid var(--cuivre-rule);
  border-radius: 22px;
  box-shadow: 0 26px 54px -36px color-mix(in srgb, var(--cuivre-blue) 60%, transparent);
}

.cuivre-contact__eyebrow {
  justify-content: center;
}

.cuivre-contact__heading {
  margin-top: 1rem;
}

.cuivre-contact__subheading {
  margin: 1rem auto 0;
  max-width: 29rem;
  font-family: var(--cuivre-font-sans);
  font-size: 0.96rem;
  line-height: 1.65;
  color: var(--cuivre-muted);
}

.cuivre-contact__actions {
  position: relative;
  margin-top: 1.9rem;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.85rem;
}

.cuivre-contact__details {
  position: relative;
  margin: 2.3rem auto 0;
  max-width: 27rem;
  border-top: 1px solid var(--cuivre-rule);
}

.cuivre-contact__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1.4rem;
  padding: 0.8rem 0.2rem;
  border-bottom: 1px solid color-mix(in srgb, var(--cuivre-ink) 9%, transparent);
}

.cuivre-contact__row-label {
  font-family: var(--cuivre-font-sans);
  font-weight: 600;
  font-size: 0.68rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--cuivre-muted);
}

.cuivre-contact__row-value {
  margin: 0;
  font-family: var(--cuivre-font-sans);
  font-size: 0.92rem;
  color: var(--cuivre-ink);
  text-align: right;
  overflow-wrap: anywhere;
}

.cuivre-contact__link {
  color: inherit;
  text-decoration: none;
  transition: color 0.2s ease;
}

.cuivre-contact__link:hover {
  color: var(--cuivre-blue);
}
</style>
