import type { PostHog } from 'posthog-js'

/**
 * Behavioural tracking for demo sites (PostHog).
 *
 * Tracking is enabled ONLY for live demos (status === 'active'); it is never
 * initialised on a delivered/sold site. Uses in-memory persistence (no cookies)
 * to stay frictionless and lighter on RGPD. All custom events carry a
 * ``demo_slug`` super property so the API can read them back per prospect.
 */
let initialized = false

/**
 * Composable exposing the demo tracking initialiser.
 * @returns An object with the ``init`` method.
 */
export function useDemoTracking(): { init: (slug: string, status: string, variant: string | null) => Promise<void> } {
  const config = useRuntimeConfig()

  /**
   * Attach DOM listeners that translate interactions into PostHog events.
   * @param posthog - Initialised PostHog instance.
   */
  function setupListeners(posthog: PostHog): void {
    const reachedDepths = new Set<number>()
    const startedAt = Date.now()

    document.addEventListener(
      'click',
      (event: MouseEvent): void => {
        const target = event.target as HTMLElement | null
        if (!target) return
        const anchor = target.closest('a')
        const href = anchor?.getAttribute('href') ?? ''
        if (href.startsWith('tel:')) {
          posthog.capture('demo_phone_click', { href })
        } else if (href.startsWith('mailto:')) {
          posthog.capture('demo_contact_click', { href })
        } else if (anchor || target.closest('button')) {
          const label = (anchor ?? target).textContent?.trim().slice(0, 80) ?? ''
          posthog.capture('demo_cta_click', { label, href })
        }
      },
      { passive: true },
    )

    window.addEventListener(
      'scroll',
      (): void => {
        const scrollable = document.documentElement.scrollHeight - window.innerHeight
        if (scrollable <= 0) return
        const percent = Math.round((window.scrollY / scrollable) * 100)
        for (const threshold of [25, 50, 75, 100]) {
          if (percent >= threshold && !reachedDepths.has(threshold)) {
            reachedDepths.add(threshold)
            posthog.capture('demo_scroll_depth', { depth: threshold })
          }
        }
      },
      { passive: true },
    )

    /** Capture total time spent when the page is hidden or unloaded. */
    const sendTime = (): void => {
      const seconds = Math.round((Date.now() - startedAt) / 1000)
      if (seconds > 0) {
        posthog.capture('demo_time_on_page', { seconds })
      }
    }

    document.addEventListener('visibilitychange', (): void => {
      if (document.visibilityState === 'hidden') sendTime()
    })
    window.addEventListener('pagehide', sendTime)
  }

  /**
   * Initialise PostHog tracking for a demo page (no-op unless it's a live demo).
   * @param slug - Demo slug (used as a super property for server-side querying).
   * @param status - Demo site status; tracking runs only when 'active'.
   * @param variant - Optional A/B variant from the email link.
   */
  async function init(slug: string, status: string, variant: string | null): Promise<void> {
    if (!import.meta.client || initialized) return
    const key = String(config.public.posthogProjectApiKey ?? '')
    const host = String(config.public.posthogIngestionHost ?? '')
    // Never track a delivered/sold site, and skip when PostHog is not configured.
    if (!key || status !== 'active') return

    const { default: posthog } = await import('posthog-js')
    posthog.init(key, {
      api_host: host,
      capture_pageview: true,
      autocapture: false,
      persistence: 'memory',
      // Identité = le slug de la démo (= identité des events email côté serveur),
      // pour que les funnels relient email ↔ démo sur la même "personne".
      bootstrap: { distinctID: slug, isIdentifiedID: true },
      // Session replay activé (sans bandeau cookie). On masque tous les champs
      // de saisie pour ne pas capter de données personnelles tapées par le visiteur.
      disable_session_recording: false,
      session_recording: {
        maskAllInputs: true,
      },
    })
    posthog.register({ demo_slug: slug, ...(variant ? { ab_variant: variant } : {}) })
    initialized = true
    setupListeners(posthog)
  }

  return { init }
}
