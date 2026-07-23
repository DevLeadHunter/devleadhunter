import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'

export type CookieConsent = 'unknown' | 'accepted' | 'refused'

/** localStorage key holding the visitor's choice. */
const STORAGE_KEY: string = 'dlh_cookie_consent'

/** Shared reactive consent state (module-level → one source of truth across the app). */
const consentState: Ref<CookieConsent> = ref('unknown')

/** Whether the stored choice has already been read from localStorage. */
let hydrated: boolean = false

/**
 * Read the stored choice once, on the client.
 */
function hydrate(): void {
  if (hydrated || !import.meta.client) return
  hydrated = true
  const stored: string | null = window.localStorage.getItem(STORAGE_KEY)
  if (stored === 'accepted' || stored === 'refused') {
    consentState.value = stored
  }
}

/**
 * Cookie-consent state for the marketing site (opt-in for analytics cookies).
 *
 * Umami is cookieless (CNIL-exempt) and runs regardless; PostHog sets cookies, so
 * it only initialises once the visitor has accepted. The choice is persisted in
 * localStorage so the banner is shown only once.
 * @returns Reactive consent state and its setters.
 */
export function useCookieConsent(): {
  consent: Ref<CookieConsent>
  hasAnalyticsConsent: ComputedRef<boolean>
  needsChoice: ComputedRef<boolean>
  accept: () => void
  refuse: () => void
} {
  hydrate()

  /** True once the visitor has accepted analytics cookies. */
  const hasAnalyticsConsent: ComputedRef<boolean> = computed((): boolean => consentState.value === 'accepted')

  /** True while no choice has been made yet (banner should be shown). */
  const needsChoice: ComputedRef<boolean> = computed((): boolean => consentState.value === 'unknown')

  /**
   * Persist a consent choice and update the shared state.
   * @param value - The choice to store.
   */
  function persist(value: CookieConsent): void {
    consentState.value = value
    if (import.meta.client) {
      window.localStorage.setItem(STORAGE_KEY, value)
    }
  }

  /**
   * Accept analytics cookies (enables PostHog).
   */
  function accept(): void {
    persist('accepted')
  }

  /**
   * Decline analytics cookies (PostHog stays off; only cookieless Umami runs).
   */
  function refuse(): void {
    persist('refused')
  }

  return { consent: consentState, hasAnalyticsConsent, needsChoice, accept, refuse }
}
