<template>
  <div v-if="pending" class="ia ia--message" :style="accentStyle">Chargement…</div>
  <div v-else-if="!assistant" class="ia ia--message ia--error" :style="accentStyle">
    Assistant introuvable ou inactif.
  </div>
  <div v-else class="ia" :style="accentStyle">
    <header class="ia__top">
      <span class="ia__logo">{{ shortBusinessName }}</span>
      <span class="ia__live"><span class="ia__live-dot" />En ligne</span>
    </header>

    <main class="ia__hero">
      <div class="ia__halo" aria-hidden="true" />
      <p class="ia__kicker">{{ shortBusinessName }} · assistant en ligne</p>
      <h1 class="ia__title">Plus aucune demande sans réponse<span class="ia__dot">.</span></h1>
      <p class="ia__lede">
        Le soir, le week-end ou quand vous êtes occupé, <em>{{ assistant.assistant_name }}</em> répond à vos clients à
        votre place et vous transmet chaque demande.
      </p>

      <ul class="ia__values">
        <li class="ia__value">
          <span class="ia__value-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7v5l3 2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
          <p class="ia__value-title">Répond 24&nbsp;h/24</p>
          <p class="ia__value-text">
            {{ assistant.assistant_name }} répond en quelques secondes, jour et nuit, même quand c'est fermé, en
            {{ languagesLabel }}.
          </p>
        </li>
        <li class="ia__value">
          <span class="ia__value-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
              <path
                d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"
                stroke-linejoin="round"
              />
              <circle cx="12" cy="13" r="3" />
            </svg>
          </span>
          <p class="ia__value-title">Un devis sur photo</p>
          <p class="ia__value-text">
            Le client envoie une photo : {{ assistant.assistant_name }} décrit le problème, pose les bonnes questions et
            vous transmet la demande de devis.
          </p>
        </li>
        <li class="ia__value">
          <span class="ia__value-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
              <rect x="3.5" y="5" width="17" height="15" rx="2" />
              <path d="M3.5 10h17M8 3v4M16 3v4" stroke-linecap="round" />
            </svg>
          </span>
          <p class="ia__value-title">Les rendez-vous demandés</p>
          <p class="ia__value-text">
            {{ capitalizedSubjectPronoun }} note la demande de rendez-vous, le besoin et les coordonnées, et vous
            prévient aussitôt.
          </p>
        </li>
      </ul>

      <section v-if="closedHours" class="ia__estimate" aria-label="Estimation d'après vos horaires Google">
        <p class="ia__estimate-kicker">Estimation · chez vous, chaque mois</p>
        <p class="ia__estimate-figure">≈&nbsp;{{ closedHours.estimated_requests }}&nbsp;demandes</p>
        <p class="ia__estimate-text">
          arrivent quand c'est fermé : {{ assistant.assistant_name }} y répond. Le calcul :
          {{ closedHours.monthly_requests }} demandes par mois (notre hypothèse pour {{ closedHours.trade_label }}) ×
          {{ closedHours.closed_share_pct }}&nbsp;%, la part du temps fermé entre 7&nbsp;h et 22&nbsp;h, quand vos
          clients cherchent, d'après vos horaires Google ({{ closedHours.open_hours_per_week }}&nbsp;h d'ouverture par
          semaine, {{ closedHours.closed_hours_in_month }}&nbsp;h fermées en {{ closedHoursMonth }}).
        </p>
      </section>

      <p v-if="priceLabel" class="ia__price">
        <strong>{{ priceLabel }}</strong
        >, installation comprise, sans engagement, premier mois satisfait ou remboursé.
      </p>

      <p class="ia__cue">Essayez : posez une question, envoyez une photo, demandez un rendez-vous, en bas à droite →</p>

      <p v-if="ownerNameLabel" class="ia__signature">
        Assistant réalisé pour {{ shortBusinessName }} par {{ ownerNameLabel }}, développeur web
      </p>
    </main>

    <AssistantChat :config="assistant" />
    <AssistantContactBanner
      :slug="assistant.slug"
      :business-name="assistant.business_name"
      :owner-name="assistant.owner_name ?? null"
      :owner-photo-url="assistant.owner_profile_photo_url ?? null"
      :owner-phone="assistant.owner_contact_phone ?? null"
      :owner-email="assistant.owner_contact_email ?? null"
      :status="assistant.status"
      :accent-color="assistant.accent_color"
    />
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import { computed, onMounted } from 'vue'
import type { AiAssistantClosedHours, AiAssistantConfig } from '~/types/AiAssistant'
import { DemoBeaconUtils } from '~/utils/DemoBeaconUtils'
import { AssistantAccentUtils } from '~/utils/AssistantAccentUtils'
import { AssistantPersonaUtils } from '~/utils/AssistantPersonaUtils'
import { BusinessNameUtils } from '~/utils/BusinessNameUtils'
import { useDemoTracking } from '~/composables/useDemoTracking'

const route: ReturnType<typeof useRoute> = useRoute()
const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
const slug: ComputedRef<string> = computed((): string => String(route.params.slug ?? ''))

const { data: assistant, pending }: Awaited<ReturnType<typeof useAsyncData<AiAssistantConfig | null | undefined>>> =
  await useAsyncData<AiAssistantConfig | null>(
    () => `assistant-${slug.value}`,
    async (): Promise<AiAssistantConfig | null> => {
      try {
        return await $fetch<AiAssistantConfig>(`${config.public.apiBase}/api/v1/ai-assistants/public/${slug.value}`)
      } catch {
        return null
      }
    },
  )

/** French names of the languages the widget can speak, for the value section. */
const LANGUAGE_NAMES: Record<string, string> = {
  fr: 'français',
  nl: 'néerlandais',
  de: 'allemand',
  en: 'anglais',
  lu: 'luxembourgeois',
  it: 'italien',
  es: 'espagnol',
}

/** The assistant's languages as a natural French list (« français, néerlandais et anglais »). */
const languagesLabel: ComputedRef<string> = computed((): string => {
  const names: string[] = (assistant.value?.languages ?? []).map((code: string): string => LANGUAGE_NAMES[code] ?? code)
  if (names.length === 0) return 'plusieurs langues'
  if (names.length === 1) return names[0] ?? 'plusieurs langues'
  return `${names.slice(0, -1).join(', ')} et ${names[names.length - 1]}`
})

const shortBusinessName: ComputedRef<string> = computed((): string =>
  BusinessNameUtils.short(assistant.value?.business_name ?? ''),
)

/** Owner name for the signature line (empty when the owner set no name). */
const ownerNameLabel: ComputedRef<string> = computed((): string => (assistant.value?.owner_name ?? '').trim())

const capitalizedSubjectPronoun: ComputedRef<string> = computed((): string =>
  AssistantPersonaUtils.capitalizedSubjectPronoun(assistant.value?.assistant_gender),
)

/**
 * The monthly price a demo shows (« 79 €/mois », formatted by the API like the emails); empty once the
 * assistant is sold, and right after the checkout (the payment may not be recorded yet).
 */
const priceLabel: ComputedRef<string> = computed((): string => {
  const label: string | null | undefined = assistant.value?.monthly_price_label
  if (!label || route.query.subscribed === '1') return ''
  return `${label}/mois`
})

/** French month names, January first, for the closed-hours estimate. */
const MONTH_NAMES: string[] = [
  'janvier',
  'février',
  'mars',
  'avril',
  'mai',
  'juin',
  'juillet',
  'août',
  'septembre',
  'octobre',
  'novembre',
  'décembre',
]

/** The estimate of a demo, shown from two requests a month while the business is closed (null otherwise). */
const closedHours: ComputedRef<AiAssistantClosedHours | null> = computed((): AiAssistantClosedHours | null => {
  const estimate: AiAssistantClosedHours | null | undefined = assistant.value?.closed_hours
  return estimate && estimate.estimated_requests >= 2 ? estimate : null
})

/** The month of the estimate, in French (« septembre »). */
const closedHoursMonth: ComputedRef<string> = computed(
  (): string => MONTH_NAMES[(closedHours.value?.month ?? 1) - 1] ?? 'ce mois-ci',
)

/** Bind the business's own accent colour to the page (falls back to the editorial gold). */
const accentStyle: ComputedRef<Record<string, string>> = computed((): Record<string, string> => ({
  '--a-accent': assistant.value?.accent_color || AssistantAccentUtils.FALLBACK_ACCENT,
}))

const { init: initTracking }: ReturnType<typeof useDemoTracking> = useDemoTracking()

onMounted((): void => {
  const current: AiAssistantConfig | null | undefined = assistant.value
  if (!current) return
  void initTracking(current.slug, current.status, null, DemoBeaconUtils.channelFromQuery(route.query.src), 'assistant')
})

useHead({
  title: computed((): string => assistant.value?.business_name ?? 'Assistant'),
  link: [
    {
      rel: 'stylesheet',
      href: 'https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,400&family=Inter:wght@400;500;600&display=swap',
    },
  ],
})
</script>

<style scoped>
.ia {
  --ia-paper: #f7f3ec;
  --ia-ink: #17130d;
  --ia-ink-dim: #6d665b;
  --ia-line: rgba(23, 19, 13, 0.12);
  --ia-card: #fffdf9;
  overflow-x: clip;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: var(--ia-paper);
  color: var(--ia-ink);
  font-family: Inter, system-ui, sans-serif;
}

.ia--message {
  align-items: center;
  justify-content: center;
  font-size: 15px;
  color: var(--ia-ink-dim);
}

.ia--error {
  color: #9f3a2f;
}

/* ── Top bar ────────────────────────────────────────────────────────────── */
.ia__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--ia-line);
  padding: 20px 24px;
}

.ia__logo {
  font-family: Fraunces, Georgia, serif;
  font-size: 1.4rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.ia__live {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--ia-ink-dim);
  white-space: nowrap;
}

.ia__live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--a-accent);
  animation: ia-pulse 2.4s ease-out infinite;
}

@keyframes ia-pulse {
  0% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--a-accent) 45%, transparent);
  }
  70% {
    box-shadow: 0 0 0 7px transparent;
  }
}

/* ── Hero ───────────────────────────────────────────────────────────────── */
.ia__hero {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
  padding: clamp(48px, 9vh, 104px) 24px 48px;
}

.ia__halo {
  position: absolute;
  top: 8%;
  left: -10%;
  width: 60%;
  height: 55%;
  background: radial-gradient(closest-side, color-mix(in srgb, var(--a-accent) 15%, transparent), transparent 72%);
  pointer-events: none;
  z-index: 0;
}

.ia__hero > :not(.ia__halo) {
  position: relative;
  z-index: 1;
}

.ia__kicker {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--ia-ink-dim);
}

.ia__kicker::before {
  content: '';
  width: 26px;
  height: 2px;
  background: var(--a-accent);
}

.ia__title {
  margin: 20px 0 0;
  font-family: Fraunces, Georgia, serif;
  font-weight: 600;
  font-size: clamp(38px, 7vw, 64px);
  line-height: 1.02;
  letter-spacing: -0.02em;
  text-wrap: balance;
}

.ia__dot {
  color: var(--a-accent);
}

.ia__lede {
  margin: 20px 0 0;
  max-width: 48ch;
  font-size: clamp(15px, 2.2vw, 17px);
  line-height: 1.6;
  color: var(--ia-ink-dim);
}

.ia__lede em {
  font-style: normal;
  font-weight: 600;
  color: var(--ia-ink);
}

/* ── Value cards ────────────────────────────────────────────────────────── */
.ia__values {
  list-style: none;
  margin: clamp(36px, 6vh, 52px) 0 0;
  padding: 0;
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.ia__value {
  border: 1px solid var(--ia-line);
  border-radius: 16px;
  background: var(--ia-card);
  padding: 18px;
  box-shadow: 0 12px 30px -24px rgba(23, 19, 13, 0.4);
}

.ia__value-icon {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  color: var(--a-accent);
  background: color-mix(in srgb, var(--a-accent) 13%, #fff);
}

.ia__value-icon svg {
  width: 21px;
  height: 21px;
}

.ia__value-title {
  margin: 14px 0 5px;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--ia-ink);
}

.ia__value-text {
  margin: 0;
  font-size: 0.86rem;
  line-height: 1.5;
  color: var(--ia-ink-dim);
}

/* ── Closed-hours estimate ───────────────────────────────────────────────── */
.ia__estimate {
  margin: clamp(22px, 3.5vh, 30px) 0 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 6px 20px;
  border: 1px solid var(--ia-line);
  border-left: 3px solid var(--a-accent);
  border-radius: 16px;
  background: var(--ia-card);
  padding: 16px 20px;
  box-shadow: 0 12px 30px -24px rgba(23, 19, 13, 0.4);
}

.ia__estimate-kicker {
  grid-column: 1 / -1;
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--ia-ink-dim);
}

/* In ink, not in the business's colour: a light brand colour would not read on the card. */
.ia__estimate-figure {
  margin: 0;
  font-family: Fraunces, Georgia, serif;
  font-size: clamp(30px, 5vw, 40px);
  font-weight: 600;
  line-height: 1;
  color: var(--ia-ink);
  white-space: nowrap;
}

.ia__estimate-text {
  margin: 0;
  font-size: 0.92rem;
  line-height: 1.5;
  color: var(--ia-ink-dim);
}

.ia__price {
  margin: clamp(26px, 4vh, 36px) 0 0;
  font-size: 0.95rem;
  line-height: 1.5;
  color: var(--ia-ink-dim);
}

.ia__price strong {
  font-weight: 600;
  color: var(--ia-ink);
}

.ia__cue {
  margin: clamp(30px, 5vh, 44px) 0 0;
  font-size: 0.92rem;
  font-weight: 500;
  color: var(--a-accent);
}

.ia__signature {
  margin: clamp(36px, 7vh, 64px) 0 0;
  font-size: 12.5px;
  color: var(--ia-ink-dim);
}

/* ── Entrance animation ─────────────────────────────────────────────────── */
@media (prefers-reduced-motion: no-preference) {
  .ia__kicker,
  .ia__title,
  .ia__lede,
  .ia__values,
  .ia__estimate,
  .ia__price,
  .ia__cue,
  .ia__signature {
    animation-name: ia-rise;
    animation-duration: 0.55s;
    animation-timing-function: cubic-bezier(0.2, 0.7, 0.3, 1);
    animation-fill-mode: both;
  }
  .ia__title {
    animation-delay: 0.05s;
  }
  .ia__lede {
    animation-delay: 0.1s;
  }
  .ia__values {
    animation-delay: 0.16s;
  }
  .ia__estimate {
    animation-delay: 0.18s;
  }
  .ia__price {
    animation-delay: 0.2s;
  }
  .ia__cue {
    animation-delay: 0.24s;
  }
  .ia__signature {
    animation-delay: 0.3s;
  }
}

@keyframes ia-rise {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@media (max-width: 640px) {
  .ia__hero {
    padding: 36px 22px 136px;
  }
  .ia__values {
    grid-template-columns: 1fr;
  }
  .ia__estimate {
    grid-template-columns: 1fr;
  }
}
</style>
