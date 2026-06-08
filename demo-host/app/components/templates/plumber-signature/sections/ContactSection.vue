<template>
  <section id="contact" class="contact">
    <div class="contact-grid">
      <div class="contact-info">
        <p class="kicker">Contact</p>
        <h2 class="section-title reveal" data-reveal>{{ contact.heading || 'Parlons de votre projet' }}</h2>
        <p v-if="contact.subheading" class="section-lede reveal" data-reveal style="--d: 80ms">{{ contact.subheading }}</p>
        <dl class="contact-rows">
          <div v-if="phone" class="contact-row">
            <svg viewBox="0 0 24 24" class="ico" aria-hidden="true" v-html="icon('phone')" />
            <div><dt>Téléphone</dt><dd><a :href="`tel:${phoneHref}`">{{ phone }}</a></dd></div>
          </div>
          <div v-if="email" class="contact-row">
            <svg viewBox="0 0 24 24" class="ico" aria-hidden="true" v-html="icon('mail')" />
            <div><dt>Email</dt><dd><a :href="`mailto:${email}`">{{ email }}</a></dd></div>
          </div>
          <div v-if="city" class="contact-row">
            <svg viewBox="0 0 24 24" class="ico" aria-hidden="true" v-html="icon('pin')" />
            <div><dt>Zone d'intervention</dt><dd>{{ city }}</dd></div>
          </div>
          <div class="contact-row">
            <svg viewBox="0 0 24 24" class="ico" aria-hidden="true" v-html="icon('clock')" />
            <div><dt>Horaires</dt><dd>{{ contact.hours || 'Lun–Sam 8 h–20 h · Urgences 24 h/24' }}</dd></div>
          </div>
        </dl>
      </div>

      <form v-if="email" class="contact-form reveal" data-reveal @submit="submitDevis">
        <p class="form-title">Demande de devis gratuit</p>
        <label class="field">
          <span>Nom</span>
          <input name="nom" type="text" autocomplete="name" required placeholder="Votre nom" />
        </label>
        <label class="field">
          <span>Téléphone</span>
          <input name="tel" type="tel" autocomplete="tel" required placeholder="06 12 34 56 78" />
        </label>
        <label class="field">
          <span>Votre besoin</span>
          <textarea name="message" rows="4" required placeholder="Décrivez votre problème ou votre projet…"></textarea>
        </label>
        <button type="submit" class="btn btn-signal form-submit">
          <span>Envoyer la demande</span>
          <svg viewBox="0 0 24 24" class="ico" aria-hidden="true" v-html="icon('arrow')" />
        </button>
        <p class="form-note">Réponse rapide — devis sans engagement.</p>
      </form>
      <div v-else class="contact-callcard reveal" data-reveal>
        <p class="form-title">Devis gratuit</p>
        <p class="callcard-sub">Appelez directement, on évalue votre besoin et on vous donne un prix clair.</p>
        <a v-if="phone" :href="`tel:${phoneHref}`" class="btn btn-signal form-submit">
          <svg viewBox="0 0 24 24" class="ico" aria-hidden="true" v-html="icon('phone')" />
          <span>{{ phone }}</span>
        </a>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { ContactBlock } from '../types'
import { icon } from '../utils'

const props = defineProps<{
  contact: ContactBlock
  phone: string
  phoneHref: string
  email: string
  city: string
  businessName: string
}>()

/* ── Formulaire devis → mailto (fonctionne sans backend) ── */
function submitDevis(e: Event): void {
  e.preventDefault()
  if (!props.email) return
  const form = e.target as HTMLFormElement
  const data = new FormData(form)
  const nom = String(data.get('nom') || '')
  const tel = String(data.get('tel') || '')
  const message = String(data.get('message') || '')
  const subject = encodeURIComponent(`Demande de devis — ${props.businessName}`)
  const body = encodeURIComponent(`Nom : ${nom}\nTéléphone : ${tel}\n\n${message}`)
  window.location.href = `mailto:${props.email}?subject=${subject}&body=${body}`
}
</script>

<style scoped>
/* ════════════ Contact ════════════ */
.contact {
  padding: clamp(3.5rem, 7vw, 6rem) 0;
}
.contact-grid {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 1.5rem;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: clamp(2rem, 5vw, 4rem);
  align-items: start;
}
.contact-rows {
  margin-top: 2rem;
  display: flex;
  flex-direction: column;
}
.contact-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.1rem 0;
  border-top: 1px solid var(--hair);
}
.contact-row:last-child {
  border-bottom: 1px solid var(--hair);
}
.contact-row .ico {
  flex: none;
  width: 1.4rem;
  height: 1.4rem;
  color: var(--brand);
}
.contact-row dt {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--ink-soft);
}
.contact-row dd {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.contact-row dd a:hover {
  color: var(--brand);
}

.contact-form,
.contact-callcard {
  background: var(--paper-2);
  border: 1px solid var(--hair);
  border-radius: 20px;
  padding: clamp(1.5rem, 3vw, 2.2rem);
}
.form-title {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700;
  font-size: 1.3rem;
  letter-spacing: -0.01em;
  margin-bottom: 1.2rem;
}
.field {
  display: block;
  margin-bottom: 1rem;
}
.field > span {
  display: block;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-soft);
  margin-bottom: 0.4rem;
}
.field input,
.field textarea {
  width: 100%;
  font: inherit;
  color: var(--ink);
  background: var(--paper);
  border: 1.5px solid var(--hair);
  border-radius: 11px;
  padding: 0.75rem 0.9rem;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}
.field input::placeholder,
.field textarea::placeholder {
  color: color-mix(in srgb, var(--ink) 38%, var(--paper));
}
.field input:focus,
.field textarea:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--brand) 18%, transparent);
}
.field textarea {
  resize: vertical;
}
.form-submit {
  width: 100%;
  margin-top: 0.4rem;
}
.form-note {
  margin-top: 0.9rem;
  text-align: center;
  font-size: 0.82rem;
  color: var(--ink-soft);
}
.callcard-sub {
  color: var(--ink-soft);
  margin-bottom: 1.4rem;
}

/* ════════════ Responsive ════════════ */
@media (max-width: 980px) {
  .contact-grid {
    grid-template-columns: 1fr;
  }
}
</style>
