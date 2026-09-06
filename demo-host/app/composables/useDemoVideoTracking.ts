import type { PostHog } from 'posthog-js'
import type { DemoVideoEvent, DemoVideoEventCapture } from '~/types/demoVideoTracking'
import { DemoBeaconUtils } from '~/utils/DemoBeaconUtils'

let initialized: boolean = false
let instance: PostHog | null = null
let beaconSlug: string = ''
let beaconBase: string = ''

// Video events worth a real-time owner notification (the rest stay analytics-only).
const VIDEO_BEACON_EVENTS: Set<string> = new Set(['demo_video_play', 'demo_video_complete', 'demo_video_replay'])

/**
 * First-party proxy path for PostHog, same as `useDemoTracking` — a branded path
 * that stays off the adblock/ETP lists (never a bare ingestion host).
 */
const POSTHOG_PROXY_PATH: string = '/dibodev/events'
/** PostHog EU UI host (toolbar / replay links only, never an ingestion target). */
const POSTHOG_UI_HOST: string = 'https://eu.posthog.com'

/**
 * PostHog tracking for the prospection-video player page (/v/{slug}).
 *
 * `distinct_id` is the demo slug, like `useDemoTracking`, so video events land on the SAME
 * person as the email and demo events and feed the email → vidéo → démo funnel.
 *
 * @returns `init` (call once with the slug) and `capture` (no-op until init).
 */
export function useDemoVideoTracking(): {
  init: (slug: string, variant: string | null, channel: string) => Promise<void>
  capture: DemoVideoEventCapture
} {
  const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()

  /**
   * Initialise PostHog for the player page (no-op when the key is missing).
   * @param slug - Demo slug (PostHog identity, shared with email/demo events).
   * @param variant - Optional A/B variant from the email link (`?v=`).
   * @param channel - Marketing channel that brought the visit ('email' / 'sms' / 'direct').
   */
  async function init(slug: string, variant: string | null, channel: string): Promise<void> {
    if (!import.meta.client || initialized) return
    // The owner's own visit (?internal=1 / ?_edit=1) must not track or notify.
    if (DemoBeaconUtils.isInternalVisit()) return
    const key: string = String(config.public.posthogProjectApiKey ?? '')
    if (!key) return

    const {
      default: posthog,
    }: typeof import('C:/Users/leogu/Desktop/Projects/devleadhunter/demo-host/node_modules/posthog-js/dist/module') =
      await import('posthog-js')
    posthog.init(key, {
      // First-party proxy — the old `posthogIngestionHost` key was never declared in
      // demo-host's runtimeConfig, so video events went to an empty host and were lost.
      api_host: POSTHOG_PROXY_PATH,
      ui_host: POSTHOG_UI_HOST,
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
    posthog.register({ surface: 'demo', demo_slug: slug, channel, ...(variant ? { ab_variant: variant } : {}) })
    initialized = true
    instance = posthog
    beaconSlug = slug
    beaconBase = String(config.public.apiBase ?? '')
    DemoBeaconUtils.send(beaconBase, beaconSlug, 'demo_video_opened')
  }

  /**
   * Capture a video event, silently ignored before init or without a PostHog key.
   * @param event - Event name.
   * @param properties - Optional event properties.
   */
  const capture: DemoVideoEventCapture = (event: DemoVideoEvent, properties?: Record<string, unknown>): void => {
    instance?.capture(event, properties)
    if (VIDEO_BEACON_EVENTS.has(event)) {
      DemoBeaconUtils.send(beaconBase, beaconSlug, event)
    }
  }

  return { init, capture }
}
