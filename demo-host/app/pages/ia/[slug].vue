<template>
  <div v-if="pending" class="ia ia--message" :style="accentStyle">Chargement…</div>
  <div v-else-if="!assistant" class="ia ia--message ia--error" :style="accentStyle">
    Assistant introuvable ou inactif.
  </div>
  <div v-else class="ia" :style="accentStyle">
    <header class="ia__top">
      <span class="ia__logo">{{ shortBusinessName }}</span>
      <span class="ia__live"><span class="ia__live-dot" />{{ assistant.assistant_name }} en ligne</span>
    </header>

    <main class="ia__page">
      <p class="ia__kicker">
        {{ shortBusinessName }}<template v-if="assistant.city"> · {{ assistant.city }}</template>
      </p>
      <h1 class="ia__title">Votre réceptionniste répond <em>déjà</em> à vos clients<span class="ia__dot">.</span></h1>
      <p class="ia__lede">
        Ce soir, 21h40. Un client cherche « {{ searchPhrase }} », tombe sur votre fiche Google et tape
        <strong>Site web</strong>. Vous êtes à table. {{ assistant.assistant_name }} répond, note sa demande, sa photo
        et ses coordonnées, et vous transmet tout.
        <strong>Essayez, comme {{ subjectPronoun }} le ferait.</strong>
      </p>

      <section class="ia__path" aria-label="Où vos clients trouvent votre réceptionniste">
        <p class="ia__label"><b>D'abord</b> · où {{ subjectPronoun }} vous trouve</p>
        <div
          class="ia__maps"
          role="img"
          :aria-label="`Votre fiche Google Maps, avec les boutons Site web et Prendre rendez-vous qui ouvrent ${assistant.assistant_name}`"
        >
          <div class="ia__maps-top">
            <div>
              <div class="ia__maps-name">{{ shortBusinessName }}</div>
              <div class="ia__maps-meta">
                <b v-if="ratingLabel">{{ ratingLabel }}</b>
                <template v-if="ratingLabel"> · </template>{{ tradeLabel
                }}<template v-if="assistant.city"> · {{ assistant.city }}</template>
              </div>
            </div>
            <span class="ia__maps-closed">Fermé ce soir</span>
          </div>
          <div class="ia__maps-actions">
            <span class="ia__maps-btn">Itinéraire</span>
            <span class="ia__maps-btn">Appeler</span>
            <span class="ia__maps-btn ia__maps-btn--lea"
              >Site web <small>→ {{ assistant.assistant_name }}</small></span
            >
            <span class="ia__maps-btn ia__maps-btn--lea">
              Prendre rendez-vous <small>→ {{ assistant.assistant_name }}</small>
            </span>
          </div>
        </div>
        <p class="ia__path-text">
          Sur votre fiche Google, les boutons <b>Site web</b> et <b>Prendre rendez-vous</b> ouvrent
          {{ assistant.assistant_name }}. Si vous avez un site, {{ subjectPronoun }} y est aussi, en bas à droite. Votre
          messagerie vocale, vos cartes et votre camionnette renvoient au même lien.
        </p>
      </section>

      <div class="ia__stage">
        <div class="ia__side">
          <p class="ia__label"><b>Votre client</b> · ce soir, 21h40</p>
          <div class="ia__device">
            <div class="ia__screen">
              <div class="ia__island" aria-hidden="true" />
              <div class="ia__statusbar" aria-hidden="true">
                <span>21:40</span>
                <span class="ia__statusbar-right">
                  <span class="ia__signal"><i /><i /><i /><i /></span>
                  <span class="ia__battery" />
                </span>
              </div>
              <div class="ia__screen-body">
                <AssistantChat :config="assistant" inline @lead-sent="onLeadSent" />
              </div>
            </div>
          </div>
        </div>

        <div class="ia__side">
          <p class="ia__label"><b>Vous</b> · quelques secondes plus tard</p>
          <div class="ia__device">
            <div class="ia__screen ia__screen--lock">
              <div class="ia__island" aria-hidden="true" />
              <div class="ia__statusbar ia__statusbar--light" aria-hidden="true">
                <span>21:43</span>
                <span class="ia__statusbar-right">
                  <span class="ia__signal"><i /><i /><i /><i /></span>
                  <span class="ia__battery" />
                </span>
              </div>
              <span class="ia__lock-date">{{ lockDateLabel }}</span>
              <span class="ia__lock-time">21:43</span>
              <span v-if="!receivedAlert" class="ia__lock-example">exemple</span>
              <div class="ia__notif" :class="{ 'ia__notif--new': receivedAlert }" aria-live="polite">
                <div class="ia__notif-app" aria-hidden="true">
                  <svg viewBox="0 0 24 24">
                    <path
                      d="M12 3C6.5 3 2.5 6.6 2.5 11c0 2.4 1.2 4.6 3.2 6.1L5 21l4.4-2.1c.8.2 1.7.3 2.6.3 5.5 0 9.5-3.6 9.5-8.1S17.5 3 12 3Z"
                      fill="#fff"
                    />
                  </svg>
                </div>
                <div class="ia__notif-body">
                  <div class="ia__notif-top"><b>Messages</b><span>maintenant</span></div>
                  <p class="ia__notif-title">{{ assistant.assistant_name }} · réceptionniste</p>
                  <p class="ia__notif-text">{{ alertText }}</p>
                </div>
              </div>
              <p class="ia__lock-hint">
                <template v-if="receivedAlert">
                  Reçu à 21h43. La fiche complète et la photo sont dans votre espace.
                </template>
                <template v-else>Terminez la conversation à gauche : ce SMS devient le vôtre.</template>
              </p>
            </div>
          </div>
        </div>
      </div>

      <div class="ia__outcomes" aria-label="Ce que vous recevez">
        <div class="ia__outcome">
          <b>Un SMS, tout de suite</b>
          <span>Le besoin, l'urgence, le numéro, la photo. L'email de résumé suit avec la conversation.</span>
        </div>
        <div class="ia__outcome">
          <b>Le rendez-vous dans votre agenda</b>
          <span>Posé dans Google Agenda, avec un rappel envoyé au client la veille.</span>
        </div>
        <div class="ia__outcome">
          <b>La fiche dans votre espace</b>
          <span>Et chaque mois, ce que {{ assistant.assistant_name }} a traité pour vous.</span>
        </div>
      </div>

      <p v-if="closedHours" class="ia__estimate">
        <b>≈ {{ closedHours.estimated_requests }} demandes par mois</b> arrivent chez vous quand c'est fermé, d'après
        vos horaires Google ({{ closedHours.closed_share_pct }} % du temps entre 7 h et 22 h) et notre hypothèse pour
        {{ closedHours.trade_label }} ({{ closedHours.monthly_requests }} demandes par mois).
        {{ assistant.assistant_name }} y répond.
      </p>

      <div v-if="priceLabel" class="ia__cta-row">
        <a :href="subscribeUrl" class="ia__cta">Je garde {{ assistant.assistant_name }}, {{ priceLabel }} par mois</a>
        <p class="ia__cta-note">
          Sans engagement, mise en place incluse, premier mois satisfait ou remboursé.<br />
          {{ assistant.assistant_name }} se présente toujours comme assistant{{ femininSuffix }} virtuel{{
            femininSuffix
          }}
          et ne donne jamais un prix à votre place.
        </p>
      </div>

      <p v-if="ownerNameLabel" class="ia__signature">
        Réceptionniste préparé{{ femininSuffix }} pour {{ shortBusinessName }} par {{ ownerNameLabel }}, développeur
        web.
      </p>
    </main>

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
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref } from 'vue'
import type { AiAssistantClosedHours, AiAssistantConfig } from '~/types/AiAssistant'
import type { AssistantLeadSummary } from '~/types/AssistantChat'
import { DemoBeaconUtils } from '~/utils/DemoBeaconUtils'
import type { AssistantAccentPalette } from '~/utils/AssistantAccentUtils'
import { AssistantAccentUtils } from '~/utils/AssistantAccentUtils'
import { AssistantDemoScenario } from '~/utils/AssistantDemoScenario'
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

/** The request the visitor sent from the phone on the left, once there is one. */
const receivedLead: Ref<AssistantLeadSummary | null> = ref(null)

const shortBusinessName: ComputedRef<string> = computed((): string =>
  BusinessNameUtils.short(assistant.value?.business_name ?? ''),
)

/** Owner name for the signature line (empty when the owner set no name). */
const ownerNameLabel: ComputedRef<string> = computed((): string => (assistant.value?.owner_name ?? '').trim())

const subjectPronoun: ComputedRef<string> = computed((): string =>
  AssistantPersonaUtils.subjectPronoun(assistant.value?.assistant_gender),
)

/** « e » after a word agreeing with a feminine persona, nothing for a masculine one. */
const femininSuffix: ComputedRef<string> = computed((): string =>
  assistant.value?.assistant_gender === 'masculine' ? '' : 'e',
)

/** What the customer types in Google (« couvreur Rennes »). */
const searchPhrase: ComputedRef<string> = computed((): string => {
  const trade: string = AssistantDemoScenario.searchWord(assistant.value?.trade_label ?? null)
  const city: string = (assistant.value?.city ?? '').trim()
  return city ? `${trade} ${city}` : trade
})

/** The trade as the Google listing shows it (« Couvreur »), or a neutral word. */
const tradeLabel: ComputedRef<string> = computed((): string => {
  const trade: string = (assistant.value?.trade_label ?? '').trim()
  return trade ? trade.charAt(0).toUpperCase() + trade.slice(1) : 'Entreprise'
})

/** « 4,8 ★ (57 avis) » when the listing has a rating. */
const ratingLabel: ComputedRef<string> = computed((): string => {
  const rating: number | null | undefined = assistant.value?.google_rating
  if (!rating) return ''
  const count: number | null | undefined = assistant.value?.google_reviews_count
  const stars: string = `${rating.toFixed(1).replace('.', ',')} ★`
  return count ? `${stars} (${count} avis)` : stars
})

/** Whether the phone on the right shows the visitor's own request rather than the example. */
const receivedAlert: ComputedRef<boolean> = computed((): boolean => receivedLead.value !== null)

/** The SMS on the business's phone: the example of the trade, then the visitor's own request. */
const alertText: ComputedRef<string> = computed((): string =>
  receivedLead.value
    ? AssistantDemoScenario.alertText(receivedLead.value)
    : AssistantDemoScenario.exampleAlertText(assistant.value?.trade_label ?? null),
)

/** Today's date on the lock screen (« jeudi 24 septembre »). */
const lockDateLabel: ComputedRef<string> = computed((): string =>
  new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date()),
)

/**
 * The monthly price a demo shows (« 79 € », formatted by the API like the emails); empty once the
 * assistant is sold, and right after the checkout (the payment may not be recorded yet).
 */
const priceLabel: ComputedRef<string> = computed((): string => {
  const label: string | null | undefined = assistant.value?.monthly_price_label
  if (!label || route.query.subscribed === '1') return ''
  return label
})

/** The permanent subscription link: each click opens a fresh Stripe Checkout. */
const subscribeUrl: ComputedRef<string> = computed(
  (): string => `${config.public.apiBase}/api/v1/ai-assistants/public/${slug.value}/subscribe?interval=month`,
)

/** The estimate of a demo, shown from two requests a month while the business is closed (null otherwise). */
const closedHours: ComputedRef<AiAssistantClosedHours | null> = computed((): AiAssistantClosedHours | null => {
  const estimate: AiAssistantClosedHours | null | undefined = assistant.value?.closed_hours
  return estimate && estimate.estimated_requests >= 2 ? estimate : null
})

/** Bind the business's own accent colour to the page (falls back to the editorial gold). */
const accentStyle: ComputedRef<Record<string, string>> = computed((): Record<string, string> => {
  const palette: AssistantAccentPalette = AssistantAccentUtils.palette(assistant.value?.accent_color)
  return { '--a-accent': palette.accent, '--a-accent-deep': palette.deep, '--a-accent-ink': palette.ink }
})

/**
 * Show on the business's phone the request the visitor just sent from the customer's phone.
 * @param summary - What the widget sent.
 */
function onLeadSent(summary: AssistantLeadSummary): void {
  receivedLead.value = summary
  if (typeof window !== 'undefined' && window.innerWidth < 760) {
    document.querySelector('.ia__screen--lock')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

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
  --ia-paper-2: #fbf9f3;
  --ia-card: #fffdf9;
  --ia-ink: #17130d;
  --ia-ink-dim: #6d665b;
  --ia-line: rgba(23, 19, 13, 0.14);
  --ia-line-soft: rgba(23, 19, 13, 0.07);
  --ia-urgent: #b8422f;
  --ia-device: #121214;
  --ia-device-edge: #2a2a2e;
  --ia-font-d: 'Fraunces', Georgia, serif;
  --ia-font-b: 'Inter', system-ui, sans-serif;
  overflow-x: clip;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: var(--ia-paper);
  color: var(--ia-ink);
  font-family: var(--ia-font-b);
  font-size: 15px;
  line-height: 1.5;
}
.ia--message {
  align-items: center;
  justify-content: center;
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
  padding: 18px 24px;
}
.ia__logo {
  font-family: var(--ia-font-d);
  font-size: 1.3rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.ia__live {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--ia-ink-dim);
  white-space: nowrap;
}
.ia__live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3fb950;
  box-shadow: 0 0 0 3px rgba(63, 185, 80, 0.2);
}

/* ── Page ───────────────────────────────────────────────────────────────── */
.ia__page {
  width: 100%;
  max-width: 860px;
  margin: 0 auto;
  padding-inline: 24px;
  padding-block: clamp(36px, 7vh, 80px) 48px;
  display: flex;
  flex-direction: column;
}
.ia__kicker {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.22em;
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
  margin: 22px 0 0;
  font-family: var(--ia-font-d);
  font-weight: 600;
  font-size: clamp(34px, 6.2vw, 56px);
  line-height: 1.04;
  letter-spacing: -0.015em;
  text-wrap: balance;
}
.ia__title em {
  font-style: italic;
  font-weight: 400;
}
.ia__dot {
  color: var(--a-accent);
}
.ia__lede {
  margin: 20px 0 0;
  max-width: 58ch;
  font-size: clamp(15px, 2.2vw, 17px);
  line-height: 1.65;
  color: var(--ia-ink-dim);
}
.ia__lede strong {
  color: var(--ia-ink);
  font-weight: 600;
}
.ia__label {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--ia-ink-dim);
}
.ia__label b {
  color: var(--ia-ink);
}

/* ── The Google listing ─────────────────────────────────────────────────── */
.ia__path {
  margin-top: clamp(30px, 5vh, 44px);
  display: grid;
  gap: 14px;
}
.ia__maps {
  border: 1px solid var(--ia-line);
  border-radius: 16px;
  background: var(--ia-card);
  padding: 16px 18px;
  display: grid;
  gap: 12px;
  box-shadow: 0 18px 40px -30px rgba(23, 19, 13, 0.4);
}
.ia__maps-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}
.ia__maps-name {
  font-family: var(--ia-font-d);
  font-weight: 600;
  font-size: 20px;
  line-height: 1.1;
}
.ia__maps-meta {
  font-size: 13px;
  color: var(--ia-ink-dim);
  margin-top: 3px;
}
.ia__maps-meta b {
  color: #c98a1a;
  font-weight: 600;
}
.ia__maps-closed {
  font-size: 12.5px;
  color: var(--ia-urgent);
  white-space: nowrap;
}
.ia__maps-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.ia__maps-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 13px;
  border-radius: 999px;
  border: 1px solid var(--ia-line);
  font-size: 13px;
  font-weight: 500;
  color: var(--ia-ink);
  background: var(--ia-paper-2);
}
.ia__maps-btn--lea {
  border-color: var(--a-accent);
  color: var(--a-accent-deep);
  background: color-mix(in srgb, var(--a-accent) 10%, var(--ia-card));
}
.ia__maps-btn--lea small {
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.85;
}
.ia__path-text {
  margin: 0;
  font-size: 14.5px;
  line-height: 1.6;
  color: var(--ia-ink-dim);
  max-width: 64ch;
}
.ia__path-text b {
  color: var(--ia-ink);
}

/* ── The scene: two phones ──────────────────────────────────────────────── */
.ia__stage {
  position: relative;
  margin-top: clamp(30px, 5vh, 48px);
  display: grid;
  grid-template-columns: 1fr;
  gap: 34px;
  justify-items: center;
}
@media (min-width: 760px) {
  .ia__stage {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 40px;
    align-items: start;
  }
}
.ia__stage::before {
  content: '';
  position: absolute;
  inset: 6% -6% 6% -6%;
  background: radial-gradient(closest-side, color-mix(in srgb, var(--a-accent) 18%, transparent), transparent 74%);
  z-index: 0;
  pointer-events: none;
}
.ia__side {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 14px;
  justify-items: center;
  width: 100%;
  min-width: 0;
}
.ia__device {
  width: min(100%, 350px);
  border-radius: 48px;
  background: var(--ia-device);
  padding: 11px;
  box-shadow:
    0 0 0 1px var(--ia-device-edge),
    0 34px 70px -30px rgba(23, 19, 13, 0.55);
}
.ia__screen {
  position: relative;
  height: 660px;
  border-radius: 38px;
  overflow: hidden;
  background: #fbf9f3;
  display: flex;
  flex-direction: column;
}
.ia__screen-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.ia__screen-body :deep(.ai-widget--inline) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.ia__screen-body :deep(.ai-panel--inline) {
  flex: 1;
  min-height: 0;
  height: auto;
}
.ia__island {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  width: 96px;
  height: 28px;
  border-radius: 999px;
  background: #000;
  z-index: 5;
}
.ia__statusbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 26px 6px;
  font-size: 14px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.ia__statusbar--light {
  color: #fff;
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
}
.ia__statusbar-right {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.ia__signal {
  display: inline-flex;
  align-items: flex-end;
  gap: 2px;
  height: 11px;
}
.ia__signal i {
  width: 3px;
  background: currentColor;
  border-radius: 1px;
}
.ia__signal i:nth-child(1) {
  height: 4px;
}
.ia__signal i:nth-child(2) {
  height: 6px;
}
.ia__signal i:nth-child(3) {
  height: 8px;
}
.ia__signal i:nth-child(4) {
  height: 11px;
}
.ia__battery {
  width: 24px;
  height: 11px;
  border: 1.5px solid currentColor;
  border-radius: 4px;
  position: relative;
}
.ia__battery::after {
  content: '';
  position: absolute;
  inset: 2px;
  right: 6px;
  background: currentColor;
  border-radius: 1px;
}

/* The business's phone: lock screen and the SMS */
.ia__screen--lock {
  background:
    radial-gradient(120% 80% at 20% 0%, rgba(120, 160, 190, 0.55), transparent 60%),
    radial-gradient(90% 70% at 90% 100%, rgba(180, 120, 90, 0.35), transparent 60%),
    linear-gradient(180deg, #1c2a36 0%, #0f151c 100%);
  color: #fff;
  align-items: center;
  padding: 60px 16px 0;
  gap: 6px;
}
.ia__lock-date {
  font-size: 15px;
  font-weight: 500;
  opacity: 0.9;
}
.ia__lock-time {
  font-size: 76px;
  font-weight: 500;
  line-height: 1;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}
.ia__lock-example {
  position: absolute;
  top: 184px;
  right: 22px;
  font-size: 10.5px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.6;
}
.ia__notif {
  position: absolute;
  left: 12px;
  right: 12px;
  top: 200px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.92);
  color: #111;
  padding: 12px 14px 12px 12px;
  display: grid;
  grid-template-columns: 42px 1fr;
  gap: 10px;
  box-shadow: 0 18px 40px -18px rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(10px);
}
.ia__notif--new {
  animation: ia-drop 0.45s cubic-bezier(0.2, 0.7, 0.3, 1);
}
@keyframes ia-drop {
  from {
    transform: translateY(-16px);
    opacity: 0;
  }
  to {
    transform: none;
    opacity: 1;
  }
}
.ia__notif-app {
  width: 42px;
  height: 42px;
  border-radius: 11px;
  background: linear-gradient(180deg, #5cd66b, #28b544);
  display: grid;
  place-items: center;
}
.ia__notif-app svg {
  width: 26px;
  height: 26px;
}
.ia__notif-body {
  min-width: 0;
}
.ia__notif-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  font-size: 12px;
  color: #555;
}
.ia__notif-top b {
  color: #111;
  font-weight: 600;
}
.ia__notif-title {
  margin: 2px 0 0;
  font-size: 14px;
  font-weight: 600;
}
.ia__notif-text {
  margin: 2px 0 0;
  font-size: 13.5px;
  line-height: 1.4;
  color: #222;
  overflow-wrap: anywhere;
}
.ia__lock-hint {
  position: absolute;
  left: 24px;
  right: 24px;
  bottom: 44px;
  margin: 0;
  font-size: 12.5px;
  opacity: 0.75;
  text-align: center;
}

/* ── Outcomes, estimate, CTA, signature ────────────────────────────────── */
.ia__outcomes {
  margin-top: clamp(30px, 5vh, 44px);
  padding-top: 22px;
  border-top: 1px solid var(--ia-line);
  display: grid;
  gap: 14px;
  grid-template-columns: 1fr;
}
@media (min-width: 620px) {
  .ia__outcomes {
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
  }
}
.ia__outcome {
  display: grid;
  gap: 4px;
}
.ia__outcome b {
  font-family: var(--ia-font-d);
  font-weight: 600;
  font-size: 18px;
}
.ia__outcome span {
  font-size: 13.5px;
  color: var(--ia-ink-dim);
  line-height: 1.5;
}
.ia__estimate {
  margin: 26px 0 0;
  padding: 14px 18px;
  border-radius: 14px;
  border: 1px solid var(--ia-line);
  background: var(--ia-card);
  font-size: 14px;
  line-height: 1.6;
  color: var(--ia-ink-dim);
}
.ia__estimate b {
  color: var(--ia-ink);
  font-weight: 600;
}
.ia__cta-row {
  margin-top: clamp(30px, 5vh, 44px);
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 14px;
}
.ia__cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 16px 32px;
  border: 0;
  border-radius: 999px;
  background: var(--ia-ink);
  color: var(--ia-paper);
  font-weight: 600;
  font-size: 15.5px;
  text-decoration: none;
  text-align: center;
  box-shadow: 0 10px 28px -12px rgba(23, 19, 13, 0.5);
  transition:
    transform 0.15s,
    box-shadow 0.15s;
}
.ia__cta:hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 34px -12px rgba(23, 19, 13, 0.55);
}
.ia__cta-note {
  margin: 0;
  text-align: center;
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--ia-ink-dim);
}
.ia__signature {
  margin: clamp(36px, 7vh, 64px) 0 0;
  padding-top: 18px;
  border-top: 1px solid var(--ia-line);
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--ia-ink-dim);
  text-align: center;
}
@media (prefers-reduced-motion: reduce) {
  .ia__notif--new {
    animation: none;
  }
}
@media (max-width: 640px) {
  .ia__top {
    padding: 14px 18px;
  }
  .ia__page {
    padding-inline: 18px;
  }
  .ia__device {
    border-radius: 40px;
    padding: 9px;
  }
  .ia__screen {
    border-radius: 32px;
    height: 620px;
  }
}
</style>
