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
 * Attach play/progress/complete tracking to the player element.
 * @param player - The mounted video element.
 */
function setupPlayerTracking(player: HTMLVideoElement): void {
  let playFired = false
  let completeFired = false
  const reachedThresholds = new Set<number>()

  player.addEventListener('play', (): void => {
    if (playFired) return
    playFired = true
    capture('demo_video_play')
  })

  player.addEventListener('timeupdate', (): void => {
    if (!player.duration || Number.isNaN(player.duration)) return
    const percent = (player.currentTime / player.duration) * 100
    for (const threshold of [25, 50, 75]) {
      if (percent >= threshold && !reachedThresholds.has(threshold)) {
        reachedThresholds.add(threshold)
        capture('demo_video_progress', { percent: threshold })
      }
    }
    if (percent >= 95 && !completeFired) {
      completeFired = true
      capture('demo_video_complete')
    }
  })
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
