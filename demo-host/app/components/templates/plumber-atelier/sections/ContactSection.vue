<template>
  <section id="contact" class="contact">
    <div class="contact-grid">
      <div class="contact-lead">
        <p class="contact-kicker">{{ contact.heading || 'Un problème de plomberie ?' }}</p>
        <a v-if="phone" :href="`tel:${phone}`" class="contact-phone">{{ phone }}</a>
        <p v-if="contact.subheading || true" class="contact-sub">
          {{ contact.subheading || 'Réponse sous 2h · Devis gratuit · Intervention rapide' }}
        </p>
        <a v-if="phone" :href="`tel:${phone}`" class="btn btn-brass contact-btn">
          <svg viewBox="0 0 24 24" class="ico" aria-hidden="true"><path d="M3 5a2 2 0 0 1 2-2h2.4a1 1 0 0 1 1 .8l.9 4a1 1 0 0 1-.5 1.1L7.5 10a11 11 0 0 0 5.5 5.5l1.1-1.3a1 1 0 0 1 1.1-.5l4 .9a1 1 0 0 1 .8 1V18a2 2 0 0 1-2 2A15 15 0 0 1 3 5Z"/></svg>
          <span>Appeler maintenant</span>
        </a>
      </div>
      <dl class="contact-meta">
        <div v-if="contact.email" class="contact-metarow">
          <svg viewBox="0 0 24 24" class="ico" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>
          <div><dt>Email</dt><dd>{{ contact.email }}</dd></div>
        </div>
        <div v-if="city" class="contact-metarow">
          <svg viewBox="0 0 24 24" class="ico" aria-hidden="true"><path d="M12 21s7-5.5 7-11a7 7 0 0 0-14 0c0 5.5 7 11 7 11Z"/><circle cx="12" cy="10" r="2.5"/></svg>
          <div><dt>Zone d'intervention</dt><dd>{{ city }}</dd></div>
        </div>
        <div class="contact-metarow">
          <svg viewBox="0 0 24 24" class="ico" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
          <div><dt>Disponibilité</dt><dd>{{ hero.badge || 'Urgences 7j/7' }}</dd></div>
        </div>
      </dl>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { ContactBlock, HeroBlock } from '../types'

defineProps<{
  contact: ContactBlock
  hero: HeroBlock
  phone: string
  city: string
}>()
</script>

<style scoped>
.contact {
  background: var(--ink);
  color: var(--paper);
  padding: clamp(3.5rem, 8vw, 6.5rem) 0;
}
.contact-grid {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
  display: grid;
  grid-template-columns: 7fr 5fr;
  gap: clamp(2rem, 5vw, 4rem);
  align-items: center;
}
.contact-kicker {
  font-family: 'Fraunces', serif;
  font-weight: 600;
  font-size: clamp(1.8rem, 3.5vw, 2.8rem);
  line-height: 1.05;
  letter-spacing: -0.02em;
  max-width: 16ch;
}
.contact-phone {
  display: block;
  font-family: 'Archivo', sans-serif;
  font-weight: 800;
  font-size: clamp(2.4rem, 7vw, 4.6rem);
  line-height: 1;
  letter-spacing: -0.03em;
  color: var(--brass);
  margin: 1.4rem 0 0;
  font-variant-numeric: tabular-nums;
  transition: opacity 0.18s ease;
}
.contact-phone:hover {
  opacity: 0.82;
}
.contact-sub {
  margin-top: 1rem;
  color: color-mix(in srgb, var(--paper) 72%, transparent);
}
.contact-btn {
  margin-top: 2rem;
  box-shadow: 4px 4px 0 color-mix(in srgb, var(--paper) 30%, transparent);
}
.contact-btn:hover {
  box-shadow: 6px 6px 0 color-mix(in srgb, var(--paper) 30%, transparent);
}
.contact-meta {
  display: flex;
  flex-direction: column;
}
.contact-metarow {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.1rem 0;
  border-top: 1px solid color-mix(in srgb, var(--paper) 18%, transparent);
}
.contact-metarow:last-child {
  border-bottom: 1px solid color-mix(in srgb, var(--paper) 18%, transparent);
}
.contact-metarow .ico {
  flex: none;
  width: 1.5rem;
  height: 1.5rem;
  color: var(--brass);
}
.contact-metarow dt {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: color-mix(in srgb, var(--paper) 60%, transparent);
}
.contact-metarow dd {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

/* ════════════ Responsive ════════════ */
@media (max-width: 860px) {
  .contact-grid {
    grid-template-columns: 1fr;
  }
}
</style>
