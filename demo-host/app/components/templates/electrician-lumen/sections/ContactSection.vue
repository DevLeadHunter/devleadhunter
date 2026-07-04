<template>
  <section id="contact" class="lumen-contact" aria-label="Contact">
    <div class="lumen-container">
      <div class="lumen-contact__panel" data-lumen-reveal>
        <p class="lumen-kicker lumen-contact__kicker">Contact</p>
        <h2 class="lumen-heading lumen-contact__heading">{{ contact.heading }}</h2>
        <p v-if="contact.subheading" class="lumen-contact__subheading">{{ contact.subheading }}</p>

        <div class="lumen-contact__actions">
          <a v-if="contact.phone" class="lumen-btn lumen-btn--primary" :href="`tel:${contact.phone}`">
            <LumenIcon name="phone" class="lumen-btn__icon" />
            {{ contact.ctaLabel }}
          </a>
          <a v-if="contact.email" class="lumen-btn lumen-btn--ghost" :href="`mailto:${contact.email}?subject=Demande de devis`">
            <LumenIcon name="mail" class="lumen-btn__icon" />
            Écrire un e-mail
          </a>
        </div>

        <dl class="lumen-contact__details">
          <div v-if="contact.phone" class="lumen-contact__row">
            <dt class="lumen-contact__row-label">Téléphone</dt>
            <dd class="lumen-contact__row-value">
              <a :href="`tel:${contact.phone}`" class="lumen-contact__link">{{ contact.phone }}</a>
            </dd>
          </div>
          <div v-if="contact.email" class="lumen-contact__row">
            <dt class="lumen-contact__row-label">E-mail</dt>
            <dd class="lumen-contact__row-value">
              <a :href="`mailto:${contact.email}`" class="lumen-contact__link">{{ contact.email }}</a>
            </dd>
          </div>
          <div v-if="contact.hours" class="lumen-contact__row">
            <dt class="lumen-contact__row-label">Horaires</dt>
            <dd class="lumen-contact__row-value">{{ contact.hours }}</dd>
          </div>
          <div v-if="contact.city" class="lumen-contact__row">
            <dt class="lumen-contact__row-label">Secteur</dt>
            <dd class="lumen-contact__row-value">{{ contact.city }}</dd>
          </div>
        </dl>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Section contact finale : panneau lumineux avec double CTA (appel + e-mail)
 * et fiche d'informations (téléphone, e-mail, horaires enrichis, secteur).
 */
import LumenIcon from './LumenIcon.vue'
import type { LumenContactContent } from '../types'

defineProps<{
  contact: LumenContactContent
}>()
</script>

<style scoped>
.lumen-contact {
  padding: 5.5rem 0 6rem;
}

.lumen-contact__panel {
  position: relative;
  max-width: 52rem;
  margin-inline: auto;
  padding: clamp(2.2rem, 5vw, 3.6rem);
  text-align: center;
  background:
    radial-gradient(ellipse 75% 60% at 50% 0%, color-mix(in srgb, var(--lumen-yellow) 9%, transparent), transparent 70%),
    var(--lumen-panel);
  border: 1px solid color-mix(in srgb, var(--lumen-yellow) 22%, var(--lumen-line));
  clip-path: polygon(20px 0, 100% 0, 100% calc(100% - 20px), calc(100% - 20px) 100%, 0 100%, 0 20px);
}

.lumen-contact__kicker {
  justify-content: center;
}

.lumen-contact__heading {
  margin-top: 1rem;
  font-size: clamp(1.8rem, 4vw, 2.7rem);
}

.lumen-contact__subheading {
  margin: 1.1rem auto 0;
  max-width: 30rem;
  line-height: 1.65;
  color: var(--lumen-muted);
}

.lumen-contact__actions {
  margin-top: 2rem;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.9rem;
}

.lumen-contact__details {
  margin: 2.4rem auto 0;
  max-width: 30rem;
  border-top: 1px solid var(--lumen-line);
}

.lumen-contact__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 0.85rem 0.2rem;
  border-bottom: 1px solid color-mix(in srgb, white 6%, transparent);
}

.lumen-contact__row-label {
  font-family: var(--lumen-font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--lumen-muted);
}

.lumen-contact__row-value {
  margin: 0;
  font-size: 0.93rem;
  color: var(--lumen-text);
  text-align: right;
  overflow-wrap: anywhere;
}

.lumen-contact__link {
  color: inherit;
  text-decoration: none;
  transition: color 0.2s ease;
}

.lumen-contact__link:hover {
  color: var(--lumen-yellow);
}
</style>
