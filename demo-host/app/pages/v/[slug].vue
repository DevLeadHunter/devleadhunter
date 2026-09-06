<template>
  <div v-if="pending" class="video-page video-page--message">Chargement…</div>
  <div v-else-if="error || !site" class="video-page video-page--message video-page--error">
    Vidéo introuvable ou expirée.
  </div>
  <main v-else class="video-page" :style="paletteStyle">
    <div class="video-page__content">
      <p class="video-page__kicker">{{ kickerLabel }}</p>
      <h1 class="video-page__title">
        Votre site est <em>déjà en ligne</em><span class="video-page__accent-dot">.</span>
      </h1>
      <p class="video-page__lede">
        Vos prestations, vos photos, vos avis.
        <template v-if="videoDurationSeconds">
          <strong>{{ videoDurationSeconds }} secondes</strong> pour le découvrir en vidéo, puis parcourez-le vous-même.
        </template>
        <template v-else>Une courte vidéo pour le découvrir, puis parcourez-le vous-même.</template>
      </p>

      <div class="video-page__stage">
        <div class="video-page__frame">
          <video
            ref="playerRef"
            class="video-page__player"
            :src="videoSrc"
            :poster="posterSrc"
            playsinline
            preload="metadata"
            @loadedmetadata="readVideoDuration"
            @ended="showEndCard"
          />
          <button
            v-if="!hasStartedPlayback"
            type="button"
            class="video-page__overlay"
            aria-label="Lancer la vidéo"
            @click="startPlayback"
          >
            <span class="video-page__play video-page__pulse">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M8.5 5.9v12.2c0 1.2 1.3 1.9 2.3 1.3l9.6-6.1c.9-.6.9-2 0-2.6l-9.6-6.1c-1-.6-2.3.1-2.3 1.3z" />
              </svg>
            </span>
            <span class="video-page__play-label">Lancer la visite{{ playLabelDurationSuffix }}</span>
          </button>
          <div
            class="video-page__endcard"
            :class="{ 'video-page__endcard--visible': isEndCardVisible }"
            :aria-hidden="isEndCardVisible ? 'false' : 'true'"
          >
            <h2 class="video-page__endcard-title">C'est votre site<span class="video-page__accent-dot">.</span></h2>
            <p class="video-page__endcard-text">Parcourez-le comme vos clients le verront.</p>
            <a class="video-page__cta" :href="demoHref" @click="trackDemoLinkClick('endcard')">
              Parcourir mon site
              <svg
                class="video-page__cta-icon"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path d="M5 12h14" />
                <path d="m13 6 6 6-6 6" />
              </svg>
            </a>
            <button type="button" class="video-page__replay" @click="replayVideo">
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path d="M3 12a9 9 0 1 0 3-6.7" />
                <path d="M3 4v5h5" />
              </svg>
              Revoir la vidéo
            </button>
          </div>
        </div>
      </div>

      <div class="video-page__cta-row" :class="{ 'video-page__cta-row--hidden': isEndCardVisible }">
        <a class="video-page__cta video-page__pulse" :href="demoHref" @click="trackDemoLinkClick('page')">
          Parcourir mon site
          <svg
            class="video-page__cta-icon"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M5 12h14" />
            <path d="m13 6 6 6-6 6" />
          </svg>
        </a>
        <p class="video-page__cta-note">Déjà en ligne — parcourez-le vous-même.</p>
      </div>

      <p v-if="hasOwnerSignature" class="video-page__signature">
        Site réalisé pour {{ shortBusinessName }} par
        <a
          v-if="ownerCompanyLabel && ownerCompanyWebsiteHref"
          :href="ownerCompanyWebsiteHref"
          target="_blank"
          rel="noopener"
          >{{ ownerCompanyLabel }}</a
        >
        <template v-else-if="ownerCompanyLabel">{{ ownerCompanyLabel }}</template>
        <template v-if="ownerCompanyLabel && ownerNameLabel"> · {{ ownerNameLabel }}, développeur web</template>
        <template v-else-if="ownerNameLabel">{{ ownerNameLabel }}, développeur web</template>
      </p>
    </div>
  </main>
</template>

<script lang="ts" setup>
import type { DemoVideoEventCapture } from '~/types/demoVideoTracking'
import type { ComputedRef, Ref } from 'vue'
import type { DemoSitePublic } from '~/types/demoSite'
import { DemoBeaconUtils } from '~/utils/DemoBeaconUtils'

const FALLBACK_ACCENT_COLOR: string = '#b45309'

/** Only plain hex values may reach the page CSS — palette colors come from prospect content. */
const HEX_COLOR_PATTERN: RegExp = /^#(?:[0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i

const route: ReturnType<typeof useRoute> = useRoute()
const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
const {
  init: initVideoTracking,
  capture,
}: { init: (slug: string, variant: string | null, channel: string) => Promise<void>; capture: DemoVideoEventCapture } =
  useDemoVideoTracking()

const playerRef: Ref<HTMLVideoElement | null> = ref(null)
const videoDurationSeconds: Ref<number | null> = ref(null)
const hasStartedPlayback: Ref<boolean> = ref(false)
const isEndCardVisible: Ref<boolean> = ref(false)

const slug: ComputedRef<string> = computed((): string => String(route.params.slug ?? ''))

const abVariant: ComputedRef<string | null> = computed((): string | null => {
  const value: unknown = route.query.v
  return typeof value === 'string' && value ? value : null
})

const channel: ComputedRef<string> = computed((): string => DemoBeaconUtils.channelFromQuery(route.query.src))

const {
  data: site,
  pending,
  error,
}: Awaited<ReturnType<typeof useAsyncData<DemoSitePublic | undefined>>> = await useAsyncData<DemoSitePublic>(
  () => `demo-video-${slug.value}`,
  async (): Promise<DemoSitePublic> => {
    return await $fetch<DemoSitePublic>(`${config.public.apiBase}/api/v1/demo-sites/public/${slug.value}`)
  },
  { watch: [slug] },
)

// Les médias sont servis par Cloudflare R2 ; les routes API ne sont qu'une redirection de repli.
const videoSrc: ComputedRef<string> = computed(
  (): string => site.value?.video_url || `${config.public.apiBase}/api/v1/demo-sites/public/${slug.value}/video.mp4`,
)

const posterSrc: ComputedRef<string> = computed(
  (): string =>
    site.value?.video_thumbnail_url ||
    `${config.public.apiBase}/api/v1/demo-sites/public/${slug.value}/video-thumbnail.jpg`,
)

/** Short business name: the part before the descriptive « - » of the Maps listing. */
const shortBusinessName: ComputedRef<string> = computed((): string => {
  const name: string = site.value?.business_name ?? ''
  return name.split(/\s+[-–—]\s+/)[0]?.trim() || name
})

const prospectCity: ComputedRef<string> = computed((): string => {
  const city: unknown = site.value?.content_json?.city
  return typeof city === 'string' ? city.trim() : ''
})

const kickerLabel: ComputedRef<string> = computed((): string =>
  prospectCity.value ? `${shortBusinessName.value} · ${prospectCity.value}` : shortBusinessName.value,
)

/** Page accent: the prospect site's primary palette color, brand amber as fallback. */
const accentColor: ComputedRef<string> = computed((): string => {
  const palette: unknown = site.value?.content_json?.palette
  if (palette && typeof palette === 'object') {
    const primary: unknown = (palette as Record<string, unknown>).primary
    if (typeof primary === 'string' && HEX_COLOR_PATTERN.test(primary)) return primary
  }
  return FALLBACK_ACCENT_COLOR
})

const paletteStyle: ComputedRef<Record<string, string>> = computed((): Record<string, string> => ({
  '--vp-accent': accentColor.value,
}))

const playLabelDurationSuffix: ComputedRef<string> = computed((): string =>
  videoDurationSeconds.value ? ` — ${videoDurationSeconds.value} s` : '',
)

/** Demo link keeping the A/B variant + channel so PostHog attributes the visit (full reload on purpose). */
const demoHref: ComputedRef<string> = computed((): string => {
  const params: URLSearchParams = new URLSearchParams()
  if (abVariant.value) params.set('v', abVariant.value)
  if (channel.value !== 'direct') params.set('src', channel.value)
  const query: string = params.toString()
  return query ? `/${slug.value}?${query}` : `/${slug.value}`
})

const ownerNameLabel: ComputedRef<string> = computed((): string => (site.value?.owner_name ?? '').trim())

const ownerCompanyLabel: ComputedRef<string> = computed((): string => (site.value?.owner_company_name ?? '').trim())

/** Owner company website link, normalized to an absolute http(s) URL. */
const ownerCompanyWebsiteHref: ComputedRef<string> = computed((): string => {
  const url: string = (site.value?.owner_company_website_url ?? '').trim()
  if (!url) return ''
  return /^https?:\/\//i.test(url) ? url : `https://${url}`
})

const hasOwnerSignature: ComputedRef<boolean> = computed(
  (): boolean => Boolean(ownerNameLabel.value) || Boolean(ownerCompanyLabel.value),
)

/** Read the real clip duration (the API does not expose it) so the page can display it. */
function readVideoDuration(): void {
  const duration: number = playerRef.value?.duration ?? Number.NaN
  if (Number.isFinite(duration) && duration > 0) {
    videoDurationSeconds.value = Math.round(duration)
  }
}

/** First play: drop the custom overlay, hand over to native controls and start the clip. */
function startPlayback(): void {
  hasStartedPlayback.value = true
  if (playerRef.value) {
    playerRef.value.controls = true
    playerRef.value.play()
  }
}

/** Clip ended: the end card relays the CTA at the moment of highest intent. */
function showEndCard(): void {
  isEndCardVisible.value = true
  if (playerRef.value) playerRef.value.controls = false
  capture('demo_video_endcard_shown')
}

/** Replay from the end card (the engagement tracker emits demo_video_replay itself). */
function replayVideo(): void {
  isEndCardVisible.value = false
  if (playerRef.value) {
    playerRef.value.controls = true
    playerRef.value.currentTime = 0
    playerRef.value.play()
  }
}

/**
 * Track the demo link before the browser leaves the page.
 * @param placement - Which CTA was clicked: 'page' (below the video) or 'endcard' (end of clip).
 */
function trackDemoLinkClick(placement: 'page' | 'endcard'): void {
  capture('demo_video_cta_click', { href: demoHref.value, placement })
}

useHead({
  link: [
    {
      rel: 'stylesheet',
      href: 'https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,400&family=Inter:wght@400;500;600&display=swap',
    },
  ],
})

useSeoMeta({
  title: () => (site.value ? `${site.value.business_name} — votre site en vidéo` : 'Votre site en vidéo'),
  robots: 'noindex',
})

onMounted(async (): Promise<void> => {
  if (site.value && site.value.video_available === false) {
    await navigateTo(demoHref.value, { external: true })
    return
  }
  if (site.value) {
    await initVideoTracking(slug.value, abVariant.value, channel.value)
  }
  if (playerRef.value) {
    readVideoDuration()
    new DemoVideoEngagementTracker(playerRef.value, capture).start()
  }
})
</script>

<style scoped>
/* DevLeadHunter editorial DA; --vp-accent is injected from the prospect site palette. */
.video-page {
  --vp-accent: #b45309;
  --vp-paper: #f7f3ec;
  --vp-ink: #17130d;
  --vp-ink-dim: #6d665b;
  --vp-line: rgba(23, 19, 13, 0.14);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: var(--vp-paper);
  color: var(--vp-ink);
  font-family: Inter, system-ui, sans-serif;
}

.video-page--message {
  justify-content: center;
  font-size: 15px;
  color: var(--vp-ink-dim);
}

.video-page--error {
  color: #9f3a2f;
}

.video-page :focus-visible {
  outline: 2px solid var(--vp-accent);
  outline-offset: 3px;
  border-radius: 4px;
}

.video-page__content {
  width: 100%;
  max-width: 780px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: clamp(40px, 8vh, 96px) 24px 40px;
}

/* ── Editorial header ──────────────────────────────────────────────────── */
.video-page__kicker {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--vp-ink-dim);
}

.video-page__kicker::before {
  content: '';
  width: 26px;
  height: 2px;
  background: var(--vp-accent);
}

.video-page__title {
  margin: 22px 0 0;
  font-family: Fraunces, Georgia, serif;
  font-weight: 600;
  font-size: clamp(34px, 6.4vw, 58px);
  line-height: 1.04;
  letter-spacing: -0.015em;
  color: var(--vp-ink);
}

.video-page__title em {
  font-style: italic;
  font-weight: 400;
}

.video-page__accent-dot {
  color: var(--vp-accent);
}

.video-page__lede {
  margin: 20px 0 0;
  max-width: 54ch;
  font-size: clamp(15px, 2.2vw, 17px);
  line-height: 1.65;
  color: var(--vp-ink-dim);
}

.video-page__lede strong {
  color: var(--vp-ink);
  font-weight: 600;
}

/* ── Video: prospect-tinted wash + thin frame ──────────────────────────── */
.video-page__stage {
  position: relative;
  margin-top: clamp(28px, 5vh, 44px);
}

.video-page__stage::before {
  content: '';
  position: absolute;
  inset: -7% -9%;
  background: radial-gradient(closest-side, color-mix(in srgb, var(--vp-accent) 16%, transparent), transparent 72%);
  z-index: 0;
  pointer-events: none;
}

.video-page__frame {
  position: relative;
  z-index: 1;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid var(--vp-line);
  box-shadow: 0 24px 60px -28px rgba(23, 19, 13, 0.35);
  background: #000;
}

.video-page__player {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
}

/* Hide the browser's big central play overlay so only our custom overlay
   shows before playback (the controls bar still carries a play/pause). */
.video-page__player::-webkit-media-controls-overlay-play-button {
  display: none;
}

.video-page__overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  width: 100%;
  padding: 0;
  border: 0;
  background: linear-gradient(to top, rgba(23, 19, 13, 0.38), rgba(23, 19, 13, 0.06) 45%);
  cursor: pointer;
  transition: opacity 0.25s;
}

.video-page__play {
  width: 78px;
  height: 78px;
  border-radius: 999px;
  background: var(--vp-ink);
  color: var(--vp-paper);
  display: grid;
  place-items: center;
  box-shadow: 0 14px 38px rgba(23, 19, 13, 0.4);
  transition: transform 0.18s;
}

.video-page__overlay:hover .video-page__play {
  transform: scale(1.07);
}

.video-page__play svg {
  margin-left: 4px;
}

.video-page__play-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--vp-paper);
  background: rgba(23, 19, 13, 0.72);
  backdrop-filter: blur(6px);
  padding: 8px 16px;
  border-radius: 999px;
}

/* ── End card: the CTA at the moment of highest intent ─────────────────── */
.video-page__endcard {
  position: absolute;
  inset: 0;
  z-index: 3;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  text-align: center;
  padding: 24px;
  background: rgba(247, 243, 236, 0.96);
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition:
    opacity 0.4s,
    visibility 0.4s;
}

.video-page__endcard--visible {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}

.video-page__endcard-title {
  margin: 0;
  font-family: Fraunces, Georgia, serif;
  font-weight: 600;
  font-size: clamp(22px, 4vw, 34px);
  line-height: 1.12;
  color: var(--vp-ink);
}

.video-page__endcard-text {
  margin: 0 0 12px;
  font-size: 14.5px;
  color: var(--vp-ink-dim);
}

.video-page__replay {
  margin-top: 16px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--vp-ink-dim);
  font-size: 13px;
  cursor: pointer;
}

.video-page__replay:hover {
  color: var(--vp-ink);
}

/* ── CTA: black pill, the DA's signature shape ─────────────────────────── */
.video-page__cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 16px 32px;
  border-radius: 999px;
  background: var(--vp-ink);
  color: var(--vp-paper);
  font-weight: 600;
  font-size: 15.5px;
  text-decoration: none;
  box-shadow: 0 10px 28px -12px rgba(23, 19, 13, 0.5);
  transition:
    transform 0.15s,
    box-shadow 0.15s;
}

.video-page__cta-icon {
  flex: none;
  transition: transform 0.18s;
}

.video-page__cta:hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 34px -12px rgba(23, 19, 13, 0.55);
}

.video-page__cta:hover .video-page__cta-icon {
  transform: translateX(3px);
}

.video-page__cta-row {
  margin-top: clamp(26px, 4vh, 38px);
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
  transition:
    opacity 0.35s,
    visibility 0.35s;
}

/* Doubled selector + animation:none — the entrance animation (fill both) would keep opacity:1. */
.video-page__cta-row.video-page__cta-row--hidden {
  animation: none;
  opacity: 0;
  visibility: hidden;
}

.video-page__cta-note {
  margin: 0;
  font-size: 13.5px;
  color: var(--vp-ink-dim);
}

/* ── Owner signature ───────────────────────────────────────────────────── */
.video-page__signature {
  margin-top: auto;
  padding-top: clamp(40px, 8vh, 72px);
  font-size: 12.5px;
  color: var(--vp-ink-dim);
  text-align: center;
}

.video-page__signature a {
  color: var(--vp-ink);
  text-decoration: none;
  border-bottom: 1px solid var(--vp-line);
}

/* ── Click-nudge highlight (ported from the dashboard's .app-btn-celebrate):
     breathing halo + periodic light sweep on the CTA and the play button. ── */
.video-page__pulse {
  position: relative;
  overflow: hidden;
  animation: video-page-pulse 2.6s ease-out 1.4s infinite;
}

.video-page__pulse::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 38%;
  background: linear-gradient(105deg, transparent, rgba(247, 243, 236, 0.32), transparent);
  transform: skewX(-18deg) translateX(-160%);
  animation: video-page-shine 2.6s ease-in-out 1.6s infinite;
  pointer-events: none;
}

@keyframes video-page-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(23, 19, 13, 0.35);
  }
  55%,
  100% {
    box-shadow: 0 0 0 9px transparent;
  }
}

@keyframes video-page-shine {
  0% {
    transform: skewX(-18deg) translateX(-160%);
  }
  42%,
  100% {
    transform: skewX(-18deg) translateX(440%);
  }
}

/* ── Entrance animation ────────────────────────────────────────────────── */
@media (prefers-reduced-motion: no-preference) {
  .video-page__kicker,
  .video-page__title,
  .video-page__lede,
  .video-page__stage,
  .video-page__cta-row,
  .video-page__signature {
    animation-name: video-page-rise;
    animation-duration: 0.55s;
    animation-timing-function: cubic-bezier(0.2, 0.7, 0.3, 1);
    animation-fill-mode: both;
  }
  .video-page__title {
    animation-delay: 0.05s;
  }
  .video-page__lede {
    animation-delay: 0.1s;
  }
  .video-page__stage {
    animation-delay: 0.16s;
  }
  .video-page__cta-row {
    animation-delay: 0.24s;
  }
  .video-page__signature {
    animation-delay: 0.3s;
  }
}

@keyframes video-page-rise {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .video-page__pulse {
    animation: none;
  }
  .video-page__pulse::after {
    display: none;
  }
}

@media (max-width: 560px) {
  .video-page__cta-row {
    flex-direction: column;
    align-items: stretch;
  }
  .video-page__cta-row .video-page__cta {
    width: 100%;
  }
  .video-page__cta-note {
    text-align: center;
  }
}
</style>
