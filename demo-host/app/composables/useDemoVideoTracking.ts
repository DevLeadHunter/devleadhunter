import type { PostHog } from 'posthog-js'
import type { DemoVideoEvent, DemoVideoEventCapture } from '~/types/demoVideoTracking'

let initialized: boolean = false
let instance: PostHog | null = null

/**
 * PostHog tracking for the prospection-video player page (/v/{slug}).
 *
 * `distinct_id` is the demo slug, like `useDemoTracking`, so video events land on the SAME
 * person as the email and demo events and feed the email → vidéo → démo funnel.
 *
 * @returns `init` (call once with the slug) and `capture` (no-op until init).
 */
export function useDemoVideoTracking(): {
  init: (slug: string, variant: string | null) => Promise<void>
  capture: DemoVideoEventCapture
} {
  const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()

  /**
   * Initialise PostHog for the player page (no-op when the key is missing).
   * @param slug - Demo slug (PostHog identity, shared with email/demo events).
   * @param variant - Optional A/B variant from the email link (`?v=`).
   */
  async function init(slug: string, variant: string | null): Promise<void> {
    if (!import.meta.client || initialized) return
    const key: string = String(config.public.posthogProjectApiKey ?? '')
    const host: string = String(config.public.posthogIngestionHost ?? '')
    if (!key) return

    const {
      default: posthog,
    }: typeof import('C:/Users/leogu/Desktop/Projects/devleadhunter/demo-host/node_modules/posthog-js/dist/module') =
      await import('posthog-js')
    posthog.init(key, {
      api_host: host,
      capture_pageview: true,
      capture_pageleave: true,
      autocapture: false,
      persistence: 'memory',
      bootstrap: { distinctID: slug, isIdentifiedID: true },
      // Session replay activé comme sur la démo ; les champs de saisie sont masqués par précaution.
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
   * Capture a video event, silently ignored before init or without a PostHog key.
   * @param event - Event name.
   * @param properties - Optional event properties.
   */
  const capture: DemoVideoEventCapture = (event: DemoVideoEvent, properties?: Record<string, unknown>): void => {
    instance?.capture(event, properties)
  }

  return { init, capture }
}
