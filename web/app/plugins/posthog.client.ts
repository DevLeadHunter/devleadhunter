import type { PostHog } from 'posthog-js'
import { watch } from 'vue'

/**
 * PostHog tracking for the marketing site (``surface: 'marketing'``).
 *
 * Only the public marketing surface is tracked — never the dashboard app (routes
 * under ``/dashboard``) and never the Tauri desktop build. Autocapture is off; we
 * emit explicit ``site_*`` events plus manual ``$pageview``s, so the app stays
 * untracked and events read cleanly alongside the demo tracking (``surface: 'demo'``)
 * in the same PostHog project.
 *
 * GDPR: PostHog sets cookies, so it stays off until the visitor accepts analytics
 * cookies (see ``useCookieConsent``). Cookieless Umami runs independently. Empty
 * key → no-op.
 */
export default defineNuxtPlugin((nuxtApp): void => {
  const config = useRuntimeConfig()
  const key: string = String(config.public.posthogProjectApiKey ?? '')
  const host: string = String(config.public.posthogIngestionHost ?? '')

  // Disabled (no key), server side, or the desktop app build → provide a no-op.
  if (!import.meta.client || !key || config.public.isDesktop) {
    nuxtApp.provide('siteTrack', (): void => {})
    return
  }

  const router = useRouter()
  const { hasAnalyticsConsent } = useCookieConsent()
  let instance: PostHog | null = null

  /**
   * Whether a route belongs to the public marketing surface (everything except the app).
   * @param {string} path - Route path to test.
   * @returns {boolean} True when the path is a marketing route.
   */
  function isMarketingRoute(path: string): boolean {
    return !path.startsWith('/dashboard')
  }

  /**
   * Whether tracking may run right now (marketing route + granted consent).
   * @param {string} path - Route path to test.
   * @returns {boolean} True when an event may be captured.
   */
  function canTrack(path: string): boolean {
    return isMarketingRoute(path) && hasAnalyticsConsent.value
  }

  /**
   * Lazily initialise PostHog on the first tracked interaction.
   * @returns {Promise<PostHog>} The initialised PostHog instance.
   */
  async function ensureInstance(): Promise<PostHog> {
    if (instance) return instance
    const { default: posthog } = await import('posthog-js')
    posthog.init(key, {
      api_host: host,
      capture_pageview: false,
      capture_pageleave: true,
      autocapture: false,
    })
    posthog.register({ surface: 'marketing' })
    instance = posthog
    return instance
  }

  /**
   * Capture a manual ``$pageview`` when tracking is allowed for the given route.
   * @param {string} path - The route path being viewed.
   * @returns {Promise<void>} Resolves once the pageview has been captured (or skipped).
   */
  async function trackPageview(path: string): Promise<void> {
    if (!canTrack(path)) return
    const posthog: PostHog = await ensureInstance()
    posthog.capture('$pageview')
  }

  nuxtApp.hook('app:mounted', (): void => {
    void trackPageview(router.currentRoute.value.path)
  })
  router.afterEach((to): void => {
    void trackPageview(to.path)
  })

  // Consent granted later (banner accept) → start tracking from the current page.
  watch(hasAnalyticsConsent, (granted: boolean): void => {
    if (granted) void trackPageview(router.currentRoute.value.path)
  })

  /**
   * Capture a marketing event (no-op on the app surface or without consent).
   * @param {string} event - Event name (``site_*``).
   * @param {Record<string, unknown>} [properties] - Optional event properties.
   * @returns {void}
   */
  const siteTrack = (event: string, properties?: Record<string, unknown>): void => {
    if (!canTrack(router.currentRoute.value.path)) return
    void ensureInstance().then((posthog: PostHog): void => {
      posthog.capture(event, properties)
    })
  }

  nuxtApp.provide('siteTrack', siteTrack)
})

declare module '#app' {
  interface NuxtApp {
    /** Capture a marketing-site PostHog event (no-op on the app / when disabled). */
    $siteTrack: (event: string, properties?: Record<string, unknown>) => void
  }
}
