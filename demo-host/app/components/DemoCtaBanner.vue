<template>
  <div v-if="isVisible" data-dlh-cta-banner class="dlh-banner" :class="state === 'collapsed' ? '' : 'dlh-banner--open'">
    <!-- Collapsed pill — the discreet entry point, never covering the template's own CTAs. -->
    <button
      v-if="state === 'collapsed'"
      type="button"
      class="dlh-pill"
      :class="{ 'dlh-celebrate': !isVideoPageVariant, 'dlh-pill--wide': isVideoPageVariant }"
      @click="open"
    >
      <img v-if="ownerPhotoUrl" class="dlh-avatar dlh-avatar--pill" :src="ownerPhotoUrl" alt="" />
      <svg
        v-else
        class="dlh-icon"
        width="15"
        height="15"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#e8a33c"
        stroke-width="2.6"
        stroke-linecap="round"
        aria-hidden="true"
      >
        <path d="M12 2v20M2 12h20M4.9 4.9l14.2 14.2M19.1 4.9L4.9 19.1" />
      </svg>
      <span class="dlh-pill__text">
        <span class="dlh-pill__label">Ce site vous plaît ?</span>
        <span class="dlh-pill__hint">Laissez-moi un mot</span>
      </span>
      <svg
        class="dlh-pill__chevron"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#6b6558"
        stroke-width="2.2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M6 14l6-6 6 6" />
      </svg>
    </button>

    <!-- Expanded card (bottom sheet on mobile) — message only: the visit came from an
         email link, so the sender already has the prospect's address. -->
    <div v-else class="dlh-card">
      <div class="dlh-card__grab" aria-hidden="true"></div>
      <div class="dlh-card__head">
        <div class="dlh-card__brand">
          <svg
            class="dlh-icon"
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#e8a33c"
            stroke-width="2.6"
            stroke-linecap="round"
            aria-hidden="true"
          >
            <path d="M12 2v20M2 12h20M4.9 4.9l14.2 14.2M19.1 4.9L4.9 19.1" />
          </svg>
          <span class="dlh-card__label">Votre démo — {{ businessName }}</span>
        </div>
        <button type="button" class="dlh-card__close" aria-label="Réduire" @click="collapse">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#a09a8c"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M6 10l6 6 6-6" />
          </svg>
        </button>
      </div>

      <template v-if="state === 'open'">
        <div class="dlh-card__intro">
          <div class="dlh-card__introrow">
            <img v-if="ownerPhotoUrl" class="dlh-avatar dlh-avatar--card" :src="ownerPhotoUrl" alt="" />
            <div>
              <div class="dlh-card__title">Ce site vous plaît ?</div>
              <div v-if="ownerNameLabel" class="dlh-card__who">{{ ownerNameLabel }} · développeur web</div>
            </div>
          </div>
          <div class="dlh-card__sub">
            Cette démo a été préparée pour vous. Laissez un message, vous serez recontacté très vite.
          </div>
        </div>
        <textarea
          v-model="message"
          class="dlh-card__textarea"
          placeholder="Votre message (optionnel)"
          maxlength="1000"
          :disabled="isSending"
          @focus="onFieldFocus"
          @input="onFieldInput"
        ></textarea>
        <button type="button" class="dlh-card__submit dlh-celebrate" :disabled="isSending" @click="submit">
          {{ isSending ? 'Envoi…' : 'Je suis intéressé' }}
          <svg
            v-if="!isSending"
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#fbf9f3"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </button>
        <div v-if="hasError" class="dlh-card__error">L'envoi a échoué — réessayez dans un instant.</div>

        <!-- Direct-contact chips — quiet escape hatch under the primary form; each hidden when unset. -->
        <div v-if="hasOwnerContact" class="dlh-card__contacts">
          <a
            v-if="ownerContactPhone"
            class="dlh-contact-chip"
            :href="ownerPhoneHref"
            @click="trackOwnerContactClick('phone')"
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path
                d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.79 19.79 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"
              />
            </svg>
            {{ ownerContactPhone }}
          </a>
          <a
            v-if="ownerContactEmail"
            class="dlh-contact-chip"
            :href="ownerEmailHref"
            @click="trackOwnerContactClick('email')"
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <path d="m22 7-10 5L2 7" />
            </svg>
            {{ ownerContactEmail }}
          </a>
        </div>
      </template>

      <div v-else class="dlh-success">
        <span class="dlh-check">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path
              class="dlh-check__path"
              d="M5 12.5l4.2 4.3L19 7"
              stroke="#2f7d4e"
              stroke-width="3"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </span>
        <div class="dlh-success__title">Merci, c'est envoyé !</div>
        <div class="dlh-success__sub">Votre message est bien parti — vous serez recontacté très vite.</div>
        <button type="button" class="dlh-success__back" @click="collapse">Continuer à explorer le site</button>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import type { DemoCtaBannerProps, DemoCtaBannerState } from '~/types/DemoCtaBanner'
import type { DemoSitePublic } from '~/types/demoSite'
import { captureDemoEvent } from '~/composables/useDemoTracking'
import { DemoBeaconUtils } from '~/utils/DemoBeaconUtils'

/**
 * « Ce site vous plaît ? » lead banner overlaid on live demo pages and, via
 * ``isVideoPageVariant``, on the prospection-video page (/v/{slug}).
 *
 * The demo used to be a dead end: a prospect reading it had no way to raise
 * their hand towards the DevLeadHunter user who sent it. The banner fixes that
 * with a single optional message (the visit comes from an email link, so the
 * sender already has the prospect's address — no coordinates asked). Submission
 * beacons a ``demo_lead`` event to the public demo-events endpoint, which
 * persists a durable lead and notifies the owner in real time.
 *
 * Deliberately styled with the DevLeadHunter identity (cream / ink) so it reads
 * as an overlay on ANY template, dark or photo — never as part of the site.
 * Shown only on live demos (status ``active``), never to the owner's own visits
 * (?internal=1 / ?_edit=1 / Storyblok editor) nor inside embedded previews.
 */
const props: DemoCtaBannerProps = defineProps({
  site: {
    type: Object as PropType<DemoSitePublic>,
    required: true,
  },
  /** Video-page placement: no scroll auto-reveal, no pill pulse, wider pill. */
  isVideoPageVariant: {
    type: Boolean,
    default: false,
  },
})

const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()

const state: Ref<DemoCtaBannerState> = ref('collapsed')
const message: Ref<string> = ref('')
const isSending: Ref<boolean> = ref(false)
const hasError: Ref<boolean> = ref(false)
/** Client-only flag: the guards (iframe, internal visit) need `window`. */
const isClientReady: Ref<boolean> = ref(false)

/** Epoch ms when the pill first appeared / when the card was opened — for dwell timing. */
const shownAt: Ref<number> = ref(0)
const openedAt: Ref<number> = ref(0)
/** One-shot guards so a repeated action counts and notifies once, not on every toggle. */
const hasTrackedShown: Ref<boolean> = ref(false)
const hasOpened: Ref<boolean> = ref(false)
const hasBeaconedOpen: Ref<boolean> = ref(false)
const hasTrackedFocus: Ref<boolean> = ref(false)
const hasTrackedInput: Ref<boolean> = ref(false)
/** Set once the message is sent, so pagehide never double-counts an abandon. */
const isResolved: Ref<boolean> = ref(false)

const businessName: ComputedRef<string> = computed((): string => props.site.business_name || 'votre entreprise')

const ownerPhotoUrl: ComputedRef<string> = computed((): string => (props.site.owner_profile_photo_url ?? '').trim())

const ownerNameLabel: ComputedRef<string> = computed((): string => (props.site.owner_name ?? '').trim())

const ownerContactPhone: ComputedRef<string> = computed((): string => (props.site.owner_contact_phone ?? '').trim())

const ownerContactEmail: ComputedRef<string> = computed((): string => (props.site.owner_contact_email ?? '').trim())

/** tel: link of the owner's phone — digits (and +) only, so « 06 42 19 38 12 » dials. */
const ownerPhoneHref: ComputedRef<string> = computed(
  (): string => `tel:${ownerContactPhone.value.replace(/[^+\d]/g, '')}`,
)

const ownerEmailHref: ComputedRef<string> = computed((): string => `mailto:${ownerContactEmail.value}`)

const hasOwnerContact: ComputedRef<boolean> = computed(
  (): boolean => Boolean(ownerContactPhone.value) || Boolean(ownerContactEmail.value),
)

/** Whether the banner renders at all — live demos, real prospect visits only. */
const isVisible: ComputedRef<boolean> = computed((): boolean => {
  if (!isClientReady.value) return false
  if (props.site.status !== 'active') return false
  if (DemoBeaconUtils.isInternalVisit()) return false
  // Embedded rendering = the dashboard's scaled card preview, never a prospect.
  if (window.self !== window.top) return false
  return true
})

const apiBase: ComputedRef<string> = computed((): string => String(config.public.apiBase ?? ''))

/** Seconds the card has been open (0 before it opens). */
function openSeconds(): number {
  return openedAt.value ? Math.round((Date.now() - openedAt.value) / 1000) : 0
}

/** Whether the prospect has typed anything into the message field. */
function hasMessage(): boolean {
  return message.value.trim().length > 0
}

/** Track the funnel denominator once, when the pill first appears to a prospect. */
function trackShown(): void {
  if (hasTrackedShown.value) return
  hasTrackedShown.value = true
  shownAt.value = Date.now()
  captureDemoEvent('demo_cta_banner_shown')
}

/** Open the card from the collapsed pill — the primary intent signal (tracked + notified once). */
function open(): void {
  state.value = 'open'
  openedAt.value = Date.now()
  hasOpened.value = true
  captureDemoEvent('demo_cta_banner_open', {
    seconds_to_open: shownAt.value ? Math.round((Date.now() - shownAt.value) / 1000) : 0,
  })
  if (hasBeaconedOpen.value) return
  hasBeaconedOpen.value = true
  DemoBeaconUtils.send(apiBase.value, props.site.slug, 'demo_cta_banner_open')
}

/** Reveal the card by itself once the prospect reaches the end — no beacon (we opened it, not them). */
function autoOpen(): void {
  if (hasOpened.value || state.value !== 'collapsed') return
  hasOpened.value = true
  state.value = 'open'
  openedAt.value = Date.now()
  captureDemoEvent('demo_cta_banner_auto_open', {
    seconds_to_open: shownAt.value ? Math.round((Date.now() - shownAt.value) / 1000) : 0,
  })
}

/** End-of-page detector: when a scrollable demo is read to the bottom, reveal the form once. */
function onScroll(): void {
  if (!isVisible.value || hasOpened.value || state.value !== 'collapsed') return
  const scrollable: number = document.documentElement.scrollHeight - window.innerHeight
  if (scrollable <= 200) return
  if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 40) autoOpen()
}

/** The prospect focused the message field — about to write (tracked + notified once). */
function onFieldFocus(): void {
  if (hasTrackedFocus.value) return
  hasTrackedFocus.value = true
  captureDemoEvent('demo_cta_banner_field_focus')
  DemoBeaconUtils.send(apiBase.value, props.site.slug, 'demo_cta_banner_field_focus')
}

/** First keystroke in the message field (PostHog only — the focus already notified). */
function onFieldInput(): void {
  if (hasTrackedInput.value) return
  hasTrackedInput.value = true
  captureDemoEvent('demo_cta_banner_input')
}

/** Reduce the card back to the pill — the banner is never fully closed, only collapsed. */
function collapse(): void {
  const withMessage: boolean = hasMessage()
  captureDemoEvent('demo_cta_banner_collapse', {
    from_state: state.value,
    had_message: withMessage,
    open_seconds: openSeconds(),
  })
  // Notify only when they wrote something then backed out — a real « almost-lead » signal.
  if (withMessage) {
    DemoBeaconUtils.send(apiBase.value, props.site.slug, 'demo_cta_banner_collapse', { seconds: openSeconds() })
  }
  state.value = 'collapsed'
}

/** Beacon the lead (message optional — the click alone is the signal) and track the outcome. */
async function submit(): Promise<void> {
  if (isSending.value) return
  isSending.value = true
  hasError.value = false
  const withMessage: boolean = hasMessage()
  const messageLength: number = message.value.trim().length
  captureDemoEvent('demo_cta_banner_submit', { has_message: withMessage, message_length: messageLength })
  try {
    const channel: string = DemoBeaconUtils.channelFromQuery(new URLSearchParams(window.location.search).get('src'))
    const response: Response = await fetch(`${apiBase.value}/api/v1/demo-events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        demo_slug: props.site.slug,
        event: 'demo_lead',
        message: message.value.trim() || null,
        seconds: openSeconds(),
        channel,
      }),
    })
    if (!response.ok) throw new Error(`demo_lead beacon failed (${response.status})`)
    isResolved.value = true
    state.value = 'sent'
    captureDemoEvent('demo_cta_banner_submitted', {
      has_message: withMessage,
      message_length: messageLength,
      open_seconds: openSeconds(),
    })
  } catch {
    hasError.value = true
    captureDemoEvent('demo_cta_banner_error')
  } finally {
    isSending.value = false
  }
}

/**
 * Track a contact chip click — video page only; the demo page's global tel:/mailto: listener already beacons these.
 * @param kind - Which chip was clicked.
 */
function trackOwnerContactClick(kind: 'phone' | 'email'): void {
  if (!props.isVideoPageVariant) return
  const event: string = kind === 'phone' ? 'demo_phone_click' : 'demo_contact_click'
  captureDemoEvent(event, { source: 'cta_banner' })
  DemoBeaconUtils.send(apiBase.value, props.site.slug, event)
}

/** On tab close, flag a prospect who opened the form but left without sending. */
function onPageHide(): void {
  if (state.value !== 'open' || isResolved.value) return
  isResolved.value = true
  captureDemoEvent('demo_cta_banner_abandoned', { had_message: hasMessage(), open_seconds: openSeconds() })
  DemoBeaconUtils.send(apiBase.value, props.site.slug, 'demo_cta_banner_abandoned', { seconds: openSeconds() })
}

watch(isVisible, (visible: boolean): void => {
  if (visible) trackShown()
})

onMounted((): void => {
  isClientReady.value = true
  window.addEventListener('pagehide', onPageHide)
  // No end-of-page auto-reveal on the short video page: its form only opens on an explicit click.
  if (!props.isVideoPageVariant) window.addEventListener('scroll', onScroll, { passive: true })
})

onUnmounted((): void => {
  window.removeEventListener('pagehide', onPageHide)
  window.removeEventListener('scroll', onScroll)
})
</script>

<style scoped>
/* DevLeadHunter identity, self-contained: the banner overlays prospect templates
   of any style, so every value is literal — no template CSS can bleed in. */
.dlh-banner {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 2147483000;
  font-family:
    'IBM Plex Sans',
    system-ui,
    -apple-system,
    'Segoe UI',
    sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* ── Collapsed pill ─────────────────────────────────────────────────────── */
.dlh-pill {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 52px;
  padding: 0 16px;
  border: 1px solid #e1dbcc;
  border-radius: 999px;
  background: #fbf9f3;
  box-shadow: 0 12px 32px rgba(15, 12, 8, 0.35);
  cursor: pointer;
  --dlh-shine: rgba(29, 26, 20, 0.12);
  --dlh-pulse: rgba(29, 26, 20, 0.3);
}

.dlh-pill__text {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.2;
}

.dlh-pill__label {
  font-size: 14px;
  font-weight: 600;
  color: #1d1a14;
  white-space: nowrap;
}

.dlh-pill__hint {
  font-size: 11px;
  color: #6b6558;
  white-space: nowrap;
}

.dlh-pill__chevron {
  flex-shrink: 0;
  margin-left: auto;
}

.dlh-icon {
  flex-shrink: 0;
}

/* ── Expanded card ──────────────────────────────────────────────────────── */
.dlh-card {
  display: flex;
  flex-direction: column;
  gap: 13px;
  width: 360px;
  padding: 20px;
  border: 1px solid #e1dbcc;
  border-radius: 14px;
  background: #fbf9f3;
  box-shadow: 0 18px 48px rgba(15, 12, 8, 0.4);
  opacity: 1;
  transform: translateY(0);
  transition:
    opacity 220ms ease-out,
    transform 260ms cubic-bezier(0.32, 1.25, 0.6, 1);
}

@starting-style {
  .dlh-card {
    opacity: 0;
    transform: translateY(14px);
  }
}

.dlh-card__grab {
  display: none;
}

.dlh-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.dlh-card__brand {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.dlh-card__label {
  overflow: hidden;
  font-family: 'IBM Plex Mono', ui-monospace, SFMono-Regular, monospace;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.14em;
  color: #6b6558;
  text-transform: uppercase;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dlh-card__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  cursor: pointer;
}

.dlh-card__close:hover {
  background: #efe9db;
}

.dlh-card__intro {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.dlh-card__title {
  font-size: 19px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: #1d1a14;
}

.dlh-card__sub {
  font-size: 13px;
  line-height: 1.45;
  color: #6b6558;
}

.dlh-card__textarea {
  height: 76px;
  padding: 10px 14px;
  border: 1px solid #e1dbcc;
  border-radius: 10px;
  background: #ffffff;
  font-family: inherit;
  font-size: 15px;
  color: #1d1a14;
  resize: none;
  outline: none;
}

.dlh-card__textarea::placeholder {
  color: #a09a8c;
}

.dlh-card__textarea:focus {
  border-color: #1d1a14;
}

.dlh-card__submit {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 46px;
  border: 0;
  border-radius: 10px;
  background: #1d1a14;
  font-family: inherit;
  font-size: 15px;
  font-weight: 600;
  color: #fbf9f3;
  cursor: pointer;
  --dlh-shine: rgba(251, 249, 243, 0.32);
  --dlh-pulse: rgba(29, 26, 20, 0.4);
}

.dlh-card__submit:disabled {
  opacity: 0.6;
  cursor: default;
}

.dlh-card__error {
  font-size: 12px;
  color: #b3423a;
}

/* ── Owner contact card: photo bubble, name line, direct chips ──────────── */
.dlh-avatar {
  flex-shrink: 0;
  border: 1px solid #e1dbcc;
  border-radius: 999px;
  object-fit: cover;
}

.dlh-avatar--pill {
  width: 36px;
  height: 36px;
  margin-left: -6px;
}

.dlh-avatar--card {
  width: 44px;
  height: 44px;
}

.dlh-card__introrow {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dlh-card__who {
  margin-top: 2px;
  font-size: 12.5px;
  color: #6b6558;
}

.dlh-card__contacts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* Same quiet vocabulary as the success back button — never a rival of the primary action. */
.dlh-contact-chip {
  display: inline-flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  gap: 7px;
  height: 40px;
  min-width: 140px;
  border: 1px solid #e1dbcc;
  border-radius: 10px;
  font-size: 12.5px;
  font-weight: 500;
  color: #1d1a14;
  text-decoration: none;
  white-space: nowrap;
}

.dlh-contact-chip:hover {
  background: #efe9db;
}

.dlh-contact-chip svg {
  flex-shrink: 0;
  color: #6b6558;
}

/* Video page: cream-on-cream ground — width gives the pill the presence the pulse gives on demos. */
@media (min-width: 641px) {
  .dlh-pill--wide {
    min-width: 300px;
  }
}

/* ── Success state ──────────────────────────────────────────────────────── */
.dlh-success {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 6px 0 2px;
  text-align: center;
}

.dlh-success__title {
  font-size: 19px;
  font-weight: 600;
  color: #1d1a14;
}

.dlh-success__sub {
  max-width: 280px;
  font-size: 13px;
  line-height: 1.5;
  color: #6b6558;
}

.dlh-success__back {
  height: 44px;
  padding: 0 20px;
  border: 1px solid #e1dbcc;
  border-radius: 10px;
  background: transparent;
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  color: #1d1a14;
  cursor: pointer;
}

.dlh-success__back:hover {
  background: #efe9db;
}

/* Animated check — same recipe as the app's wizard steps (pop + stroke draw). */
.dlh-check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 999px;
  background: rgba(47, 125, 78, 0.12);
  opacity: 1;
  transform: scale(1);
  transition:
    opacity 200ms ease-out,
    transform 320ms cubic-bezier(0.34, 1.56, 0.64, 1);
}

.dlh-check svg {
  width: 26px;
  height: 26px;
}

.dlh-check__path {
  stroke-dasharray: 24;
  stroke-dashoffset: 0;
  transition: stroke-dashoffset 300ms ease-out 90ms;
}

@starting-style {
  .dlh-check {
    opacity: 0;
    transform: scale(0.3);
  }

  .dlh-check__path {
    stroke-dashoffset: 24;
  }
}

/* ── Celebrate: breathing halo + periodic light sweep (same recipe as the
      app's end-of-tunnel CTA), shine tint per element via --dlh-shine. ───── */
.dlh-celebrate {
  position: relative;
  overflow: hidden;
  animation: dlh-celebrate-pulse 2.6s ease-out 1.4s infinite;
}

.dlh-celebrate::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 38%;
  background: linear-gradient(105deg, transparent, var(--dlh-shine), transparent);
  transform: skewX(-18deg) translateX(-160%);
  animation: dlh-celebrate-shine 2.6s ease-in-out 1.6s infinite;
  pointer-events: none;
}

@keyframes dlh-celebrate-pulse {
  0% {
    box-shadow: 0 0 0 0 var(--dlh-pulse);
  }

  55%,
  100% {
    box-shadow: 0 0 0 9px transparent;
  }
}

@keyframes dlh-celebrate-shine {
  0% {
    transform: skewX(-18deg) translateX(-160%);
  }

  42%,
  100% {
    transform: skewX(-18deg) translateX(440%);
  }
}

/* ── Mobile: full-width pill, bottom-sheet card ─────────────────────────── */
@media (max-width: 640px) {
  .dlh-banner {
    right: 12px;
    left: 12px;
    bottom: calc(12px + env(safe-area-inset-bottom));
  }

  .dlh-banner--open {
    right: 0;
    left: 0;
    bottom: 0;
  }

  .dlh-pill {
    width: 100%;
  }

  .dlh-card {
    width: 100%;
    border-radius: 18px 18px 0 0;
    border-right: 0;
    border-bottom: 0;
    border-left: 0;
    padding: 10px 20px calc(22px + env(safe-area-inset-bottom));
  }

  .dlh-card__grab {
    display: block;
    width: 40px;
    height: 4px;
    margin: 0 auto 2px;
    border-radius: 999px;
    background: #e1dbcc;
  }
}

@media (prefers-reduced-motion: reduce) {
  .dlh-celebrate {
    animation: none;
  }

  .dlh-celebrate::after {
    display: none;
  }

  .dlh-card,
  .dlh-check,
  .dlh-check__path {
    transition: none;
  }
}
</style>
