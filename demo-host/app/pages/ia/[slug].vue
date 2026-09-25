<template>
  <div v-if="pending" class="ia ia--message" :style="accentStyle">Chargement…</div>
  <div v-else-if="!assistant" class="ia ia--message ia--error" :style="accentStyle">
    Cette démo n'est plus disponible.
  </div>
  <div v-else class="ia" :style="accentStyle" @focusin="onFocusChange" @focusout="onFocusChange">
    <header class="ia__top">
      <span class="ia__logo">{{ shortBusinessName }}</span>
      <span class="ia__live"><span class="ia__live-dot" />{{ assistant.assistant_name }} en ligne</span>
    </header>

    <main class="ia__page">
      <p class="ia__kicker">
        {{ shortBusinessName }}<template v-if="assistant.city"> · {{ assistant.city }}</template>
      </p>
      <h1 class="ia__title">Votre réceptionniste répond à vos clients<span class="ia__dot">.</span></h1>
      <p class="ia__lede">
        Ce soir, 21h40. Un client cherche « {{ searchPhrase }} », tombe sur votre fiche Google et tape
        <strong>Site web</strong>. Vous êtes à table. {{ assistant.assistant_name }} répond, note sa demande, sa photo
        et ses coordonnées, et vous transmet tout.
        <strong>Essayez, comme ce client le ferait.</strong>
      </p>

      <div class="ia__stage">
        <div class="ia__side">
          <p class="ia__label"><b>Votre client</b> · ce soir, 21h40</p>
          <AssistantDemoPhoneFrame time="21:40" screen="app">
            <AssistantChat :config="assistant" inline @lead-sent="onLeadSent" />
          </AssistantDemoPhoneFrame>
        </div>

        <div ref="ownerPhoneSide" class="ia__side">
          <p class="ia__label"><b>Vous</b> · quelques secondes plus tard</p>
          <AssistantDemoPhoneFrame time="21:43" screen="lock">
            <AssistantDemoLockScreen
              time="21:43"
              :date-label="lockDateLabel"
              :assistant-name="assistant.assistant_name"
              :alert-text="alertText"
              :is-example="receivedLead === null"
              :hint-text="lockHintText"
            />
          </AssistantDemoPhoneFrame>
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
          {{ assistant.assistant_name }} se présente toujours comme réceptionniste IA et ne donne jamais un prix à votre
          place.
        </p>
      </div>

      <p v-if="ownerNameLabel" class="ia__signature">
        Réceptionniste préparé{{ femininSuffix }} pour {{ shortBusinessName }} par {{ ownerNameLabel }}, développeur
        web.
      </p>
    </main>

    <div :class="{ 'ia__banner--hidden': isComposerFocused }">
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
import { AssistantDemoScenarioUtils } from '~/utils/AssistantDemoScenarioUtils'
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
/** True while the visitor types in the customer's phone: the contact pill steps aside (it would cover the keys). */
const isComposerFocused: Ref<boolean> = ref(false)
/** The business's phone, scrolled into view on a small screen once a request lands on it. */
const ownerPhoneSide: Ref<HTMLElement | null> = ref(null)

const shortBusinessName: ComputedRef<string> = computed((): string =>
  BusinessNameUtils.short(assistant.value?.business_name ?? ''),
)

/** Owner name for the signature line (empty when the owner set no name). */
const ownerNameLabel: ComputedRef<string> = computed((): string => (assistant.value?.owner_name ?? '').trim())

/** « e » after a word agreeing with a feminine persona, nothing for a masculine one. */
const femininSuffix: ComputedRef<string> = computed((): string =>
  assistant.value?.assistant_gender === 'masculine' ? '' : 'e',
)

/** What the customer types in Google (« couvreur Rennes »). */
const searchPhrase: ComputedRef<string> = computed((): string => {
  const trade: string = AssistantDemoScenarioUtils.searchWord(assistant.value?.trade_label ?? null)
  const city: string = (assistant.value?.city ?? '').trim()
  return city ? `${trade} ${city}` : trade
})

/** The SMS on the business's phone: the example of the trade, then the visitor's own request. */
const alertText: ComputedRef<string> = computed((): string =>
  receivedLead.value
    ? AssistantDemoScenarioUtils.alertText(receivedLead.value)
    : AssistantDemoScenarioUtils.exampleAlertText(assistant.value?.trade_label ?? null),
)

const lockHintText: ComputedRef<string> = computed((): string => {
  if (!receivedLead.value) return 'Terminez la conversation à gauche : ce SMS devient le vôtre.'
  const stored: string = receivedLead.value.hasPhoto ? 'La fiche complète et la photo sont' : 'La fiche complète est'
  return `Reçu à 21h43. ${stored} dans votre espace.`
})

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
  return { '--a-accent': palette.accent, '--a-accent-strong': palette.strong, '--a-accent-text': palette.text }
})

/**
 * Show on the business's phone the request the visitor just sent from the customer's phone.
 * @param summary - What the widget sent.
 */
function onLeadSent(summary: AssistantLeadSummary): void {
  receivedLead.value = summary
  if (typeof window !== 'undefined' && window.innerWidth < 760) {
    ownerPhoneSide.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

/**
 * Track whether the focus sits in a field of the inline widget.
 * @param event - The focusin or focusout event bubbling from the page.
 */
function onFocusChange(event: FocusEvent): void {
  const target: EventTarget | null = event.type === 'focusin' ? event.target : event.relatedTarget
  isComposerFocused.value =
    target instanceof HTMLElement &&
    (target instanceof HTMLTextAreaElement || target instanceof HTMLInputElement) &&
    target.closest('.ai-widget--inline') !== null
}

const { init: initTracking }: ReturnType<typeof useDemoTracking> = useDemoTracking()

onMounted((): void => {
  const current: AiAssistantConfig | null | undefined = assistant.value
  if (!current) return
  initTracking(current.slug, current.status, null, DemoBeaconUtils.channelFromQuery(route.query.src), 'assistant')
})

useHead({
  title: computed((): string => assistant.value?.business_name ?? 'Réceptionniste IA'),
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
.ia__banner--hidden :deep(.ac) {
  opacity: 0;
  pointer-events: none;
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
    /* Room to scroll the phones above the contact pill, which floats over the bottom corner. */
    padding-bottom: 100px;
  }
}
</style>
