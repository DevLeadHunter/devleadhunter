<template>
  <div v-if="pending" class="ia ia--message" :style="accentStyle">Chargement…</div>
  <div v-else-if="!assistant" class="ia ia--message ia--error" :style="accentStyle">
    Cette démo n'est plus disponible.
  </div>
  <div v-else class="ia" :style="accentStyle" @focusin="onFocusChange" @focusout="onFocusChange">
    <main class="ia__page">
      <p class="ia__kicker">
        {{ shortBusinessName }}<template v-if="assistant.city"> · {{ assistant.city }}</template>
      </p>
      <h1 class="ia__title">Votre réceptionniste répond à vos clients<span class="ia__dot">.</span></h1>
      <p class="ia__lede">
        Ce soir, 21h40, un client cherche « {{ searchPhrase }} » et ouvre votre site. Vous êtes à table.
        {{ assistant.assistant_name }} répond, note sa demande et vous la transmet.
        <strong>Essayez, comme ce client le ferait.</strong>
      </p>

      <div class="ia__stage">
        <div class="ia__side ia__side--visitor">
          <p class="ia__label">
            <b>Votre client</b> · ce soir, 21h40
            <span class="ia__live"><span class="ia__live-dot" />en direct</span>
          </p>
          <div class="ia__window">
            <AssistantChat :config="assistant" inline @lead-sent="onLeadSent" @example-played="onExamplePlayed" />
          </div>
        </div>

        <div ref="ownerFeedSide" class="ia__side ia__side--owner">
          <p class="ia__label"><b>Vous</b> · quelques secondes plus tard</p>
          <AssistantDemoOwnerFeed
            time-label="21:43"
            :assistant-name="assistant.assistant_name"
            :alert-text="alertText"
            :is-example="receivedLead === null"
            :hint-text="feedHintText"
            :arrival-key="exampleArrivals"
          />
        </div>
      </div>

      <div class="ia__outcomes" aria-label="Ce que vous recevez">
        <div class="ia__outcome">
          <b>Un SMS, tout de suite</b>
          <span>Le besoin, l'urgence, le numéro, la photo.</span>
        </div>
        <div class="ia__outcome">
          <b>Le rendez-vous dans votre agenda</b>
          <span>Google Agenda, rappel au client la veille.</span>
        </div>
        <div class="ia__outcome">
          <b>La fiche dans votre espace</b>
          <span>Et un rapport chaque mois.</span>
        </div>
      </div>

      <section class="ia__after" aria-label="Votre espace">
        <a :href="exampleSpaceUrl" class="ia__after-figure" target="_blank" rel="noopener" @click="onExampleSpaceClick">
          <img
            src="/showroom/espace-client.webp"
            alt="Votre espace : les demandes reçues par la réceptionniste, avec les coordonnées de chaque client"
            width="1400"
            height="1014"
            loading="lazy"
          />
        </a>
        <p class="ia__after-text">
          <b>Vous gardez la main.</b>
          Tout ce que {{ assistant.assistant_name }} reçoit arrive dans votre espace : demandes, photos, rapport du
          mois, réglages.
          <a :href="exampleSpaceUrl" target="_blank" rel="noopener" @click="onExampleSpaceClick">
            Voir un exemple d'espace
          </a>
        </p>
      </section>

      <p v-if="closedHours" class="ia__estimate">
        <b>≈ {{ closedHours.estimated_requests }} demandes par mois</b> arrivent quand c'est fermé ({{
          closedHours.closed_share_pct
        }}
        % du temps entre 7 h et 22 h). {{ assistant.assistant_name }} y répond.
      </p>

      <div v-if="priceLabel" class="ia__cta-row">
        <DemoCtaLink :href="subscribeUrl"
          >Je garde {{ assistant.assistant_name }}, {{ priceLabel }} par mois</DemoCtaLink
        >
        <p class="ia__cta-note">Sans engagement, mise en place incluse, premier mois satisfait ou remboursé.</p>
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
import AssistantDemoOwnerFeed from '~/components/AssistantDemoOwnerFeed.vue'
import DemoCtaLink from '~/components/DemoCtaLink.vue'
import { DemoBeaconUtils } from '~/utils/DemoBeaconUtils'
import type { AssistantAccentPalette } from '~/utils/AssistantAccentUtils'
import { AssistantAccentUtils } from '~/utils/AssistantAccentUtils'
import { AssistantDemoScenarioUtils } from '~/utils/AssistantDemoScenarioUtils'
import { BusinessNameUtils } from '~/utils/BusinessNameUtils'
import { captureDemoEvent, useDemoTracking } from '~/composables/useDemoTracking'

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

/** The request the visitor sent from the conversation, once there is one. */
const receivedLead: Ref<AssistantLeadSummary | null> = ref(null)
/** True while the visitor types in the conversation: the contact pill steps aside (it would cover the keys). */
const isComposerFocused: Ref<boolean> = ref(false)
/** The business's side, scrolled into view on a small screen once a request lands on it. */
const ownerFeedSide: Ref<HTMLElement | null> = ref(null)
/** How many times the played example has ended: each one makes the example notification land again. */
const exampleArrivals: Ref<number> = ref(0)

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

const feedHintText: ComputedRef<string> = computed((): string => {
  if (!receivedLead.value && exampleArrivals.value > 0) {
    return 'Voilà ce que vous auriez reçu. À vous : écrivez dans la conversation comme ce client le ferait.'
  }
  if (!receivedLead.value) return 'Terminez la conversation à gauche : ce SMS devient le vôtre.'
  const stored: string = receivedLead.value.hasPhoto ? 'La fiche complète et la photo sont' : 'La fiche complète est'
  return `Reçu à 21h43. ${stored} dans votre espace.`
})

/**
 * The monthly price a demo shows (« 79 € », formatted by the API like the emails); empty once the
 * assistant is sold, and right after the checkout (the payment may not be recorded yet).
 */
const priceLabel: ComputedRef<string> = computed((): string => {
  const label: string | null | undefined = assistant.value?.monthly_price_label
  if (!label || route.query.subscribed === '1') return ''
  return label
})

/** The example client space, read-only, with the way back to this demo. */
const exampleSpaceUrl: ComputedRef<string> = computed((): string => `/client/exemple?demo=${slug.value}`)

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
 * Show on the business's side the request the visitor just sent from the conversation.
 * @param summary - What the widget sent.
 */
function onLeadSent(summary: AssistantLeadSummary): void {
  receivedLead.value = summary
  revealOwnerFeed()
}

/** The prospect opens the example space: the sign that the « after » matters to them. */
function onExampleSpaceClick(): void {
  captureDemoEvent('assistant_space_example_opened')
}

/** The scripted conversation has run: the example SMS lands again on the business's side. */
function onExamplePlayed(): void {
  exampleArrivals.value += 1
  revealOwnerFeed()
}

/** On a small screen, scroll the business's side into view once something lands on it. */
function revealOwnerFeed(): void {
  if (typeof window !== 'undefined' && window.innerWidth < 900) {
    ownerFeedSide.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
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

/* ── Page: the video page's editorial column, wider for the two-column scene ─────────────────────── */
.ia__page {
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  padding-inline: 24px;
  padding-block: clamp(40px, 8vh, 96px) 48px;
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
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--ia-ink-dim);
}
.ia__label b {
  color: var(--ia-ink);
}
.ia__live {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-left: auto;
  font-size: 11px;
  letter-spacing: 0.14em;
  color: var(--ia-ink-dim);
}
.ia__live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3fb950;
  box-shadow: 0 0 0 3px rgba(63, 185, 80, 0.2);
}

/* ── The scene: the live conversation, and what the business receives ───────────────────────────── */
.ia__stage {
  position: relative;
  margin-top: clamp(30px, 5vh, 48px);
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 30px;
}
@media (min-width: 900px) {
  .ia__stage {
    grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
    gap: 32px;
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
  min-width: 0;
}
.ia__side--owner {
  align-self: start;
}
@media (min-width: 900px) {
  .ia__side--owner {
    position: sticky;
    top: 24px;
  }
}
/* The conversation, laid out as a window rather than a phone: it is the thing to try, not a picture of it. */
.ia__window {
  height: clamp(520px, 74vh, 640px);
  display: flex;
  flex-direction: column;
  border-radius: 22px;
  border: 1px solid var(--ia-line);
  background: var(--ia-card);
  box-shadow: 0 30px 70px -34px rgba(23, 19, 13, 0.45);
  overflow: hidden;
}
.ia__window :deep(.ai-widget--inline) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.ia__window :deep(.ai-panel--inline) {
  flex: 1;
  min-height: 0;
  height: auto;
}
.ia__banner--hidden :deep(.ac) {
  opacity: 0;
  pointer-events: none;
}

/* ── The space, as a picture: what the business keeps in hand ──────────── */
.ia__after {
  margin-top: clamp(30px, 5vh, 44px);
  display: grid;
  gap: 18px;
  align-items: center;
}
@media (min-width: 900px) {
  .ia__after {
    grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
    gap: 36px;
  }
}
.ia__after-figure {
  display: block;
  border-radius: 18px;
  overflow: hidden;
  border: 1px solid var(--ia-line);
  background: var(--ia-card);
  box-shadow: 0 24px 60px -30px rgba(23, 19, 13, 0.4);
  transition:
    transform 0.15s,
    box-shadow 0.15s;
}
.ia__after-figure:hover {
  transform: translateY(-2px);
  box-shadow: 0 30px 70px -30px rgba(23, 19, 13, 0.45);
}
.ia__after-figure img {
  display: block;
  width: 100%;
  height: auto;
}
.ia__after-text {
  margin: 0;
  font-size: 15px;
  line-height: 1.6;
  color: var(--ia-ink-dim);
}
.ia__after-text b {
  display: block;
  margin-bottom: 6px;
  font-family: var(--ia-font-d);
  font-weight: 600;
  font-size: 22px;
  line-height: 1.2;
  color: var(--ia-ink);
}
.ia__after-text a {
  color: var(--ia-ink);
  font-weight: 500;
  text-decoration: underline;
  text-underline-offset: 3px;
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
    gap: 28px;
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
@media (max-width: 640px) {
  .ia__page {
    padding-inline: 18px;
    /* Room to scroll the scene above the contact pill, which floats over the bottom corner. */
    padding-bottom: 100px;
  }
  .ia__window {
    height: min(560px, 78vh);
  }
}
</style>
