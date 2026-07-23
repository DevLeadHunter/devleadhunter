import type { PostHog } from 'posthog-js'

/**
 * Behavioural tracking for demo sites (PostHog).
 *
 * Tracking is enabled ONLY for live demos (status === 'active'); it is never
 * initialised on a delivered/sold site. Uses in-memory persistence (no cookies)
 * to stay frictionless and lighter on RGPD. All events carry ``surface: 'demo'``
 * (to separate them from marketing-site events in the same PostHog project) and a
 * ``demo_slug`` super property so the API can read them back per prospect.
 *
 * The goal is to understand exactly what a prospect did on the demo link we sent
 * them — which sections they read, how engaged they were, what they clicked — so
 * Léo can follow up with context. Events captured:
 *   - $pageview / $pageleave / $rageclick (PostHog)
 *   - demo_section_view   { section, position }   — a section scrolled into view
 *   - demo_scroll_depth   { depth }               — 25/50/75/100 % thresholds
 *   - demo_cta_click      { label, href, section, tag }
 *   - demo_phone_click    { href, section }
 *   - demo_contact_click  { href, section }
 *   - demo_outbound_click { href, host, section } — link to another site (maps, social…)
 *   - demo_engaged        { reason, engaged_seconds, max_scroll } — fired once when the
 *                            visit becomes "qualified" (a warm-lead signal to query on)
 *   - demo_time_on_page   { seconds, max_scroll }  — engaged (visible) time on exit
 */
let initialized = false

/** A qualified visit needs at least this many engaged seconds… */
const ENGAGED_SECONDS_THRESHOLD = 20
/** …or this much scroll depth (%). */
const ENGAGED_SCROLL_THRESHOLD = 50

/**
 * Composable exposing the demo tracking initialiser.
 * @returns An object with the ``init`` method.
 */
export function useDemoTracking(): { init: (slug: string, status: string, variant: string | null) => Promise<void> } {
  const config = useRuntimeConfig()

  /**
   * Resolve a human-readable name for the section an element belongs to.
   * Walks up to the nearest section/header/footer and derives a label from its
   * data-section / id / aria-label / first heading, so it works across templates
   * without editing each one.
   * @param element - The element that was interacted with (or observed).
   * @returns A short section name, or 'unknown'.
   */
  function sectionOf(element: HTMLElement | null): string {
    const container = element?.closest('section, header, footer, [data-section]') as HTMLElement | null
    if (!container) return 'unknown'
    const explicit = container.dataset.section || container.id || container.getAttribute('aria-label')
    if (explicit) return explicit.trim().slice(0, 40)
    const heading = container.querySelector('h1, h2, h3')?.textContent?.trim()
    if (heading) return heading.slice(0, 40)
    return container.tagName.toLowerCase()
  }

  /**
   * Attach DOM listeners that translate interactions into PostHog events.
   * @param posthog - Initialised PostHog instance.
   */
  function setupListeners(posthog: PostHog): void {
    const reachedDepths = new Set<number>()
    const seenSections = new Set<Element>()
    let maxDepth = 0
    let engagedSeconds = 0
    let lastSentSeconds = 0
    let interacted = false
    let engagedFired = false

    /**
     * Fire the one-shot ``demo_engaged`` qualified-visit signal once the visit
     * crosses any engagement threshold.
     * @param reason - What triggered qualification (click / scroll / time).
     */
    const markEngaged = (reason: string): void => {
      if (engagedFired) return
      if (!interacted && engagedSeconds < ENGAGED_SECONDS_THRESHOLD && maxDepth < ENGAGED_SCROLL_THRESHOLD) return
      engagedFired = true
      posthog.capture('demo_engaged', { reason, engaged_seconds: engagedSeconds, max_scroll: maxDepth })
    }

    // ── Clicks: phone / email / outbound / CTA, each tagged with its section ──
    document.addEventListener(
      'click',
      (event: MouseEvent): void => {
        const target = event.target as HTMLElement | null
        if (!target) return
        const anchor = target.closest('a')
        const button = target.closest('button')
        if (!anchor && !button) return

        interacted = true
        const section = sectionOf(target)
        const href = anchor?.getAttribute('href') ?? ''

        if (href.startsWith('tel:')) {
          posthog.capture('demo_phone_click', { href, section })
        } else if (href.startsWith('mailto:')) {
          posthog.capture('demo_contact_click', { href, section })
        } else if (/^https?:\/\//i.test(href) && !href.includes(window.location.host)) {
          let host: string
          try {
            host = new URL(href).host
          } catch {
            host = ''
          }
          posthog.capture('demo_outbound_click', { href, host, section })
        } else {
          const label = (anchor ?? button ?? target).textContent?.trim().slice(0, 80) ?? ''
          posthog.capture('demo_cta_click', {
            label,
            href,
            section,
            tag: (anchor ?? button)?.tagName.toLowerCase() ?? '',
          })
        }
        markEngaged('click')
      },
      { passive: true },
    )

    // ── Scroll depth thresholds + running max ────────────────────────────────
    window.addEventListener(
      'scroll',
      (): void => {
        const scrollable = document.documentElement.scrollHeight - window.innerHeight
        if (scrollable <= 0) return
        const percent = Math.round((window.scrollY / scrollable) * 100)
        if (percent > maxDepth) maxDepth = percent
        for (const threshold of [25, 50, 75, 100]) {
          if (percent >= threshold && !reachedDepths.has(threshold)) {
            reachedDepths.add(threshold)
            posthog.capture('demo_scroll_depth', { depth: threshold })
          }
        }
        markEngaged('scroll')
      },
      { passive: true },
    )

    // ── Section views (which parts of the site were actually seen) ───────────
    if (typeof IntersectionObserver !== 'undefined') {
      const observer = new IntersectionObserver(
        (entries: IntersectionObserverEntry[]): void => {
          for (const entry of entries) {
            if (!entry.isIntersecting || seenSections.has(entry.target)) continue
            seenSections.add(entry.target)
            posthog.capture('demo_section_view', {
              section: sectionOf(entry.target as HTMLElement),
              position: seenSections.size,
            })
          }
        },
        { threshold: 0.5 },
      )
      document.querySelectorAll('section, header, footer, [data-section]').forEach((el: Element): void => {
        observer.observe(el)
      })
    }

    // Ne compte que pendant que l'onglet est visible, sinon le temps de fond gonfle la mesure.
    const ticker = window.setInterval((): void => {
      if (document.visibilityState === 'visible') {
        engagedSeconds += 1
        markEngaged('time')
      }
    }, 1000)

    /** Send the engaged-time event (deduped: only when it grew since last send). */
    const sendTime = (): void => {
      if (engagedSeconds <= lastSentSeconds) return
      lastSentSeconds = engagedSeconds
      posthog.capture('demo_time_on_page', { seconds: engagedSeconds, max_scroll: maxDepth })
    }

    document.addEventListener('visibilitychange', (): void => {
      if (document.visibilityState === 'hidden') sendTime()
    })
    window.addEventListener('pagehide', (): void => {
      window.clearInterval(ticker)
      sendTime()
    })
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
      // $pageleave apporte le temps sur page calculé par PostHog, en recoupement du nôtre.
      capture_pageleave: true,
      autocapture: false,
      // Frustration signal (rageclicks) without turning on full autocapture.
      rageclick: true,
      persistence: 'memory',
      // Le slug sert aussi d'identité aux events email : un funnel email ↔ démo sur la même personne.
      bootstrap: { distinctID: slug, isIdentifiedID: true },
      // Replay sans bandeau cookie : tous les champs de saisie sont masqués.
      disable_session_recording: false,
      session_recording: {
        maskAllInputs: true,
      },
    })
    // Ne jamais renommer : les noms demo_* sont lus côté API.
    posthog.register({ surface: 'demo', demo_slug: slug, ...(variant ? { ab_variant: variant } : {}) })
    initialized = true
    setupListeners(posthog)
  }

  return { init }
}
