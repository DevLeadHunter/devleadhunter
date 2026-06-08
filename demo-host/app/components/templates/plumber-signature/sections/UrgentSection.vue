<template>
  <section class="urgent">
    <div class="urgent-inner">
      <div class="urgent-lead">
        <p class="urgent-kicker">{{ urgency.heading || 'Une fuite, une panne, une urgence ?' }}</p>
        <p class="urgent-sub">{{ urgency.subheading || 'On décroche et on intervient vite. 24 h/24, 7 j/7.' }}</p>
      </div>
      <div v-if="phone" class="urgent-call">
        <span class="urgent-avail"><span class="urgent-dot" aria-hidden="true"></span>Ligne ouverte maintenant</span>
        <a :href="`tel:${phoneHref}`" class="urgent-phone">{{ phone }}</a>
        <a :href="`tel:${phoneHref}`" class="btn btn-signal urgent-btn">
          <svg viewBox="0 0 24 24" class="ico" aria-hidden="true" v-html="icon('phone')" />
          <span>Appeler l'artisan</span>
        </a>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { UrgencyBlock } from '../types'
import { icon } from '../utils'

defineProps<{
  urgency: UrgencyBlock
  phone: string
  phoneHref: string
}>()
</script>

<style scoped>
/* ════════════ Bandeau urgence fort ════════════ */
.urgent {
  background: var(--ink);
  color: var(--paper);
  position: relative;
  overflow: hidden;
}
.urgent::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(60% 120% at 85% 50%, color-mix(in srgb, var(--signal) 24%, transparent), transparent 60%);
}
.urgent-inner {
  position: relative;
  max-width: 1240px;
  margin: 0 auto;
  padding: clamp(2.8rem, 6vw, 4.5rem) 1.5rem;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: clamp(1.5rem, 4vw, 3rem);
  align-items: center;
}
.urgent-kicker {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700;
  font-size: clamp(1.7rem, 3.6vw, 2.7rem);
  line-height: 1.05;
  letter-spacing: -0.025em;
  max-width: 18ch;
}
.urgent-sub {
  margin-top: 0.7rem;
  color: color-mix(in srgb, var(--paper) 70%, transparent);
  font-size: 1.05rem;
}
.urgent-call {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
}
.urgent-avail {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: color-mix(in srgb, var(--paper) 70%, transparent);
}
.urgent-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3ad29f;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--signal) 60%, transparent);
  }
  70% {
    box-shadow: 0 0 0 7px transparent;
  }
  100% {
    box-shadow: 0 0 0 0 transparent;
  }
}
.urgent-phone {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 800;
  font-size: clamp(2.3rem, 6vw, 3.6rem);
  line-height: 1;
  letter-spacing: -0.03em;
  color: var(--signal);
  font-variant-numeric: tabular-nums;
  transition: opacity 0.18s ease;
}
.urgent-phone:hover {
  opacity: 0.85;
}
.urgent-btn {
  margin-top: 0.5rem;
}

/* ════════════ Responsive ════════════ */
@media (max-width: 980px) {
  .urgent-inner {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .urgent-dot {
    animation: none;
  }
}
</style>
