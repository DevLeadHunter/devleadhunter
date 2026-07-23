import type { UseDesktopRuntimeReturn, UseOpenExternalUrlReturn } from '~/types/Composables'
/**
 * Open a URL in the system browser (Tauri) or a new tab (web).
 */
export function useOpenExternalUrl(): UseOpenExternalUrlReturn {
  const { isDesktopApp }: UseDesktopRuntimeReturn = useDesktopRuntime()

  /**
   * Open an external URL outside the desktop WebView when needed.
   */
  async function openExternalUrl(url: string): Promise<void> {
    if (!import.meta.client || !url) {
      return
    }

    if (isDesktopApp.value) {
      const {
        open,
      }: typeof import('C:/Users/leogu/Desktop/Projects/devleadhunter/web/node_modules/@tauri-apps/plugin-shell/dist-js/index') =
        await import('@tauri-apps/plugin-shell')
      await open(url)
      return
    }

    window.open(url, '_blank', 'noopener,noreferrer')
  }

  return { openExternalUrl }
}
