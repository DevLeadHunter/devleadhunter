import type { UseOpenExternalUrlReturn } from '~/types/Composables'
/**
 * Open a URL in the system browser (Tauri) or a new tab (web).
 */
export function useOpenExternalUrl(): UseOpenExternalUrlReturn {
  const { isDesktopApp } = useDesktopRuntime()

  /**
   * Open an external URL outside the desktop WebView when needed.
   */
  async function openExternalUrl(url: string): Promise<void> {
    if (!import.meta.client || !url) {
      return
    }

    if (isDesktopApp.value) {
      const { open } = await import('@tauri-apps/plugin-shell')
      await open(url)
      return
    }

    window.open(url, '_blank', 'noopener,noreferrer')
  }

  return { openExternalUrl }
}
