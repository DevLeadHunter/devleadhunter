import type { PostHog } from 'posthog-js'

/**
 * PostHog tracking for the prospection-video player page (/v/{slug}).
 *
 * Same identity contract as `useDemoTracking`: `distinct_id` = demo slug,
 * super properties `surface: 'demo'` + `demo_slug` (+ `ab_variant` when the
 * email link carried `?v=`), so video events land on the SAME PostHog person
 * as the email + demo events and feed the email → vidéo → démo funnel.
 *
 * Events captured (read back by the API's lead scoring / timeline):
 *   - $pageview                                  — the thumbnail click itself
 *   - demo_video_play     { }                    — first play press
 *   - demo_video_progress { percent }            — 25/50/75 % thresholds
 *   - demo_video_complete { }                    — watched ≥95 %
 *   - demo_video_cta_click { href }              — « Découvrir le site » click
 */
let initialized = false
let instance: PostHog | null = null

/**
 * Composable exposing the video-page tracking initialiser and capture helper.
 * @returns `init` (call once with the slug) and `capture` (no-op until init).
 */
export function useDemoVideoTracking(): {
  init: (slug: string, variant: string | null) => Promise<void>
  capture: (event: string, properties?: Record<string, unknown>) => void
} {
  const config = useRuntimeConfig()

  /**
   * Initialise PostHog for the player page (no-op when the key is missing).
   * @param slug - Demo slug (PostHog identity, shared with email/demo events).
   * @param variant - Optional A/B variant from the email link (`?v=`).
   */
  async function init(slug: string, variant: string | null): Promise<void> {
    if (!import.meta.client || initialized) return
    const key = String(config.public.posthogProjectApiKey ?? '')
    const host = String(config.public.posthogIngestionHost ?? '')
    if (!key) return

    const { default: posthog } = await import('posthog-js')
    posthog.init(key, {
      api_host: host,
      capture_pageview: true,
      capture_pageleave: true,
      autocapture: false,
      persistence: 'memory',
      bootstrap: { distinctID: slug, isIdentifiedID: true },
      // Pas de session replay sur la page vidéo : rien à masquer, la démo suffit.
      disable_session_recording: true,
    })
    posthog.register({ surface: 'demo', demo_slug: slug, ...(variant ? { ab_variant: variant } : {}) })
    initialized = true
    instance = posthog
  }

  /**
   * Capture a video event (silently ignored before init / without a key).
   * @param event - Event name (demo_video_*).
   * @param properties - Optional event properties.
   */
  function capture(event: string, properties?: Record<string, unknown>): void {
    instance?.capture(event, properties)
  }

  return { init, capture }
}
