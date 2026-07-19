<template>
  <div v-if="pending" class="flex min-h-screen items-center justify-center bg-neutral-950 text-neutral-300">
    Chargement…
  </div>
  <div v-else-if="error || !site" class="flex min-h-screen items-center justify-center bg-neutral-950 text-red-300">
    Vidéo introuvable ou expirée.
  </div>
  <main v-else class="relative flex min-h-screen flex-col items-center justify-center bg-neutral-950 px-4 py-10 text-white">
    <!-- Croix de fermeture — seulement quand la page est ouverte depuis l'outil
         (?from=app) : un prospect venant de l'email n'a rien à « fermer ». -->
    <button
      v-if="isOpenedFromApp"
      type="button"
      class="absolute top-5 right-5 flex h-10 w-10 cursor-pointer items-center justify-center rounded-full border border-neutral-700 !text-neutral-300 transition-colors hover:border-neutral-500 hover:!text-white"
      title="Fermer"
      aria-label="Fermer la page vidéo"
      @click="handleClose"
    >
      ✕
    </button>
    <div class="w-full max-w-3xl">
      <p class="text-xs font-semibold tracking-[0.2em] text-neutral-400 uppercase">Votre site en vidéo</p>
      <h1 class="mt-2 text-2xl font-semibold sm:text-3xl">{{ site.business_name }}</h1>
      <p class="mt-2 text-sm text-neutral-400">
        30 secondes pour découvrir le site créé pour vous — puis explorez-le en vrai.
      </p>

      <video
        ref="playerRef"
        class="mt-6 aspect-video w-full rounded-2xl border border-neutral-800 bg-black shadow-2xl"
        :src="videoSrc"
        :poster="posterSrc"
        controls
        playsinline
        preload="metadata"
      />

      <div class="mt-6 flex flex-col items-center gap-3 sm:flex-row">
        <!-- !text-neutral-950 : les layers de templates embarquent du CSS global
             non-layered (a { color … }) qui bat les utilities Tailwind v4. -->
        <a
          :href="demoHref"
          class="inline-flex w-full items-center justify-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-semibold !text-neutral-950 no-underline transition-opacity hover:opacity-90 sm:w-auto"
          @click="handleCtaClick"
        >
          Découvrir votre site en vrai
          <span aria-hidden="true">→</span>
        </a>
        <p class="text-xs text-neutral-500">Le site est en ligne — cliquez pour le parcourir vous-même.</p>
      </div>
    </div>
  </main>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { DemoSitePublic } from '~/types/demoSite'

const route = useRoute()
const config = useRuntimeConfig()
const { init, capture } = useDemoVideoTracking()

const slug: ComputedRef<string> = computed((): string => String(route.params.slug ?? ''))
const variant: ComputedRef<string | null> = computed((): string | null => {
  const value = route.query.v
  return typeof value === 'string' && value ? value : null
})

/** True when the page was opened from the DevLeadHunter dashboard (?from=app). */
const isOpenedFromApp: ComputedRef<boolean> = computed((): boolean => route.query.from === 'app')

const playerRef: Ref<HTMLVideoElement | null> = ref<HTMLVideoElement | null>(null)

const { data: site, pending, error } = await useAsyncData(
  () => `demo-video-${slug.value}`,
  async (): Promise<DemoSitePublic> => {
    return await $fetch<DemoSitePublic>(`${config.public.apiBase}/api/v1/demo-sites/public/${slug.value}`)
  },
  { watch: [slug] },
)

const videoSrc: ComputedRef<string> = computed(
  (): string => `${config.public.apiBase}/api/v1/demo-sites/public/${slug.value}/video.mp4`,
)
const posterSrc: ComputedRef<string> = computed(
  (): string => `${config.public.apiBase}/api/v1/demo-sites/public/${slug.value}/video-thumbnail.jpg`,
)

/** Demo link keeping the A/B variant for PostHog attribution (full reload on purpose). */
const demoHref: ComputedRef<string> = computed((): string => {
  return variant.value ? `/${slug.value}?v=${encodeURIComponent(variant.value)}` : `/${slug.value}`
})

/**
 * Track the « Découvrir le site » click before the full-page navigation.
 */
function handleCtaClick(): void {
  capture('demo_video_cta_click', { href: demoHref.value })
}

/**
 * Close the tab opened from the dashboard (fallback: browser history back).
 */
function handleClose(): void {
  window.close()
  if (window.history.length > 1) window.history.back()
}

/**
 * Attach exhaustive engagement tracking to the player element: play / resume /
 * pause / replay / progress / complete / real watch-time / seek / fullscreen /
 * mute. Kept property-rich so the API can score attention precisely.
 * @param player - The mounted video element.
 */
function setupPlayerTracking(player: HTMLVideoElement): void {
  let playFired = false
  let completeFired = false
  let replays = 0
  let wasEnded = false
  let lastMuted = player.muted
  let seekFromPercent = 0
  const reachedThresholds = new Set<number>()

  // Real watched time: accumulate wall-clock deltas between timeupdates while
  // playing, ignoring big gaps (pause/seek) so the number reflects attention.
  let watchedSeconds = 0
  let lastTickMs = 0
  let flushedSeconds = 0

  /** Current playback position as an integer percent (0 when duration unknown). */
  const percentNow = (): number => {
    if (!player.duration || Number.isNaN(player.duration)) return 0
    return Math.round((player.currentTime / player.duration) * 100)
  }

  /** Emit the real watched-seconds so far, only when it grew since last flush. */
  const flushWatchTime = (): void => {
    const seconds = Math.round(watchedSeconds)
    if (seconds <= flushedSeconds) return
    flushedSeconds = seconds
    capture('demo_video_watch_time', { seconds, percent: percentNow() })
  }

  // ── Play: distinguish first play / replay (restart) / resume (from pause) ──
  player.addEventListener('play', (): void => {
    if (!playFired) {
      playFired = true
      capture('demo_video_play')
    } else if (wasEnded || player.currentTime < 1) {
      replays += 1
      capture('demo_video_replay', { count: replays })
    } else {
      capture('demo_video_resume', { percent: percentNow() })
    }
    wasEnded = false
    lastTickMs = 0
  })

  // ── Pause (ignore the pause fired at the natural end of the clip) ──────────
  player.addEventListener('pause', (): void => {
    if (player.ended) return
    capture('demo_video_pause', { percent: percentNow() })
    flushWatchTime()
  })

  player.addEventListener('ended', (): void => {
    wasEnded = true
    flushWatchTime()
  })

  // ── Progress thresholds + complete + real watched-time accumulation ───────
  player.addEventListener('timeupdate', (): void => {
    const now = Date.now()
    if (lastTickMs) {
      const delta = (now - lastTickMs) / 1000
      // A normal tick is ~0.25 s; a larger gap means paused/seeked → don't count.
      if (delta > 0 && delta < 1.5) watchedSeconds += delta
    }
    lastTickMs = now

    const percent = percentNow()
    for (const threshold of [25, 50, 75]) {
      if (percent >= threshold && !reachedThresholds.has(threshold)) {
        reachedThresholds.add(threshold)
        capture('demo_video_progress', { percent: threshold })
      }
    }
    if (percent >= 95 && !completeFired) {
      completeFired = true
      capture('demo_video_complete')
      flushWatchTime()
    }
  })

  // ── Seek: he jumped forward or backward in the clip ───────────────────────
  player.addEventListener('seeking', (): void => {
    seekFromPercent = percentNow()
  })
  player.addEventListener('seeked', (): void => {
    const to = percentNow()
    lastTickMs = 0 // the seek gap must not inflate watched time
    if (Math.abs(to - seekFromPercent) < 1) return
    capture('demo_video_seek', {
      from_percent: seekFromPercent,
      to_percent: to,
      direction: to > seekFromPercent ? 'forward' : 'backward',
    })
  })

  // ── Fullscreen (standard + iOS Safari native video fullscreen) ────────────
  const onFullscreenChange = (): void => {
    capture('demo_video_fullscreen', { entered: document.fullscreenElement != null })
  }
  document.addEventListener('fullscreenchange', onFullscreenChange)
  document.addEventListener('webkitfullscreenchange', onFullscreenChange)
  player.addEventListener('webkitbeginfullscreen', (): void => capture('demo_video_fullscreen', { entered: true }))
  player.addEventListener('webkitendfullscreen', (): void => capture('demo_video_fullscreen', { entered: false }))

  // ── Mute / unmute ─────────────────────────────────────────────────────────
  player.addEventListener('volumechange', (): void => {
    if (player.muted === lastMuted) return
    lastMuted = player.muted
    capture('demo_video_mute', { muted: player.muted })
  })

  // ── Flush the watched-time when the prospect leaves or hides the tab ───────
  const flushOnHidden = (): void => {
    if (document.visibilityState === 'hidden') flushWatchTime()
  }
  document.addEventListener('visibilitychange', flushOnHidden)
  window.addEventListener('pagehide', flushWatchTime)
}

useSeoMeta({
  title: () => (site.value ? `${site.value.business_name} — votre site en vidéo` : 'Votre site en vidéo'),
  robots: 'noindex',
})

onMounted(async (): Promise<void> => {
  // Vidéo absente (pas encore générée / purgée) → on renvoie vers la démo elle-même.
  if (site.value && site.value.video_available === false) {
    await navigateTo(demoHref.value, { external: true })
    return
  }
  if (site.value) {
    await init(slug.value, variant.value)
  }
  if (playerRef.value) {
    setupPlayerTracking(playerRef.value)
  }
})
</script>
