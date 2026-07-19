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
 *   - demo_video_play      { }                   — first play press
 *   - demo_video_resume    { percent }           — play after a pause
 *   - demo_video_pause     { percent }           — pause (not the natural end)
 *   - demo_video_replay    { count }             — restarted from the beginning
 *   - demo_video_progress  { percent }           — 25/50/75 % thresholds
 *   - demo_video_complete  { }                   — watched ≥95 %
 *   - demo_video_watch_time{ seconds, percent }  — real watched seconds (flushed)
 *   - demo_video_seek      { from_percent, to_percent, direction }
 *   - demo_video_fullscreen{ entered }           — entered/left fullscreen
 *   - demo_video_mute      { muted }             — muted/unmuted
 *   - demo_video_cta_click { href }              — « Découvrir le site » click
 *
 * Session replay is enabled (like the demo) to see exactly what the prospect
 * does on the page; text inputs are masked as a precaution.
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
      // Session replay activé (comme la démo) pour voir ce que fait le prospect
      // sur la page vidéo ; on masque les champs de saisie par précaution.
      disable_session_recording: false,
      session_recording: {
        maskAllInputs: true,
      },
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
