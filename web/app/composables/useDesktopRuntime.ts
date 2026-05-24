/**
 * Detect DevLeadHunter desktop (Tauri WebView) vs plain browser — client-only, SSR-safe.
 *
 * @returns Desktop detection helpers for the Tauri shell.
 */
export function useDesktopRuntime() {
  const isDesktopApp = computed((): boolean => {
    if (!import.meta.client) {
      return false
    }
    const w = window as Window & {
      __TAURI__?: unknown
      __TAURI_INTERNALS__?: unknown
    }
    return Boolean(w.__TAURI__ || w.__TAURI_INTERNALS__)
  })

  return { isDesktopApp }
}
