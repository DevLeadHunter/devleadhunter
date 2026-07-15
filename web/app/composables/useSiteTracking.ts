/**
 * Marketing-site analytics helper (PostHog, ``surface: 'marketing'``).
 *
 * Thin wrapper over the ``$siteTrack`` plugin helper so components can fire
 * ``site_*`` events without touching PostHog directly. It is a no-op on the
 * dashboard app, on the desktop build, and when tracking is disabled.
 * @returns An object exposing ``track``.
 */
export function useSiteTracking(): {
  track: (event: string, properties?: Record<string, unknown>) => void
} {
  const { $siteTrack } = useNuxtApp()

  /**
   * Fire a marketing-site event.
   * @param event - Event name (``site_*``).
   * @param properties - Optional event properties.
   */
  function track(event: string, properties?: Record<string, unknown>): void {
    $siteTrack(event, properties)
  }

  return { track }
}
