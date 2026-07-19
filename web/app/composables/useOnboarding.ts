/**
 * Composable for the post-signup setup wizard state.
 * @module composables/useOnboarding
 */

/** localStorage key remembering that the user chose to configure later. */
const ONBOARDING_POSTPONED_KEY = 'dlh-onboarding-postponed'

/**
 * Setup-wizard helpers shared by the wizard page and the auth middleware.
 *
 * The server owns whether the wizard was *completed*; this composable only owns
 * the local « I'll do it later » choice, so a user who postpones is nudged once
 * and never trapped in a loop back to `/configuration`.
 *
 * @returns Postpone state helpers.
 */
export function useOnboarding(): {
  isPostponed: () => boolean
  postpone: () => void
  clearPostponed: () => void
} {
  /**
   * Whether the user postponed the setup on this browser.
   * @returns True when the wizard should not hijack navigation any more.
   */
  function isPostponed(): boolean {
    if (!import.meta.client) return false
    return localStorage.getItem(ONBOARDING_POSTPONED_KEY) === '1'
  }

  /** Remember that the user wants to configure later. */
  function postpone(): void {
    if (import.meta.client) localStorage.setItem(ONBOARDING_POSTPONED_KEY, '1')
  }

  /** Forget the postponement (used when the wizard is opened again on purpose). */
  function clearPostponed(): void {
    if (import.meta.client) localStorage.removeItem(ONBOARDING_POSTPONED_KEY)
  }

  return { isPostponed, postpone, clearPostponed }
}
