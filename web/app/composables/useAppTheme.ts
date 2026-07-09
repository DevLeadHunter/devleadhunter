import type { Ref } from 'vue'
import type { AppTheme } from '~/types/AppTheme'
import { watch } from 'vue'

/** localStorage key persisting the dashboard theme choice. */
const APP_THEME_STORAGE_KEY = 'dlh-app-theme'

/**
 * Dashboard theme state (light paper / dark warm ink).
 *
 * The theme value is bound as ``data-theme`` on the dashboard root by the
 * layout; this composable also mirrors it as a ``dark`` class on ``<html>``
 * so Nuxt UI components follow the same mode.
 *
 * @returns Theme ref plus init/toggle helpers.
 */
export function useAppTheme(): {
  theme: Ref<AppTheme>
  initTheme: () => void
  toggleTheme: () => void
} {
  const theme: Ref<AppTheme> = useState<AppTheme>('app-theme', (): AppTheme => 'light')

  /**
   * Mirror the current theme on ``<html>`` for Nuxt UI (Tailwind `dark` class).
   */
  function applyThemeToDocument(): void {
    if (import.meta.client) {
      document.documentElement.classList.toggle('dark', theme.value === 'dark')
    }
  }

  /**
   * Load the persisted theme (client-side) and apply it to the document.
   */
  function initTheme(): void {
    if (import.meta.client) {
      const stored: string | null = localStorage.getItem(APP_THEME_STORAGE_KEY)
      if (stored === 'light' || stored === 'dark') {
        theme.value = stored
      }
      applyThemeToDocument()
    }
  }

  /**
   * Switch between light and dark, persist and apply the choice.
   */
  function toggleTheme(): void {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    if (import.meta.client) {
      localStorage.setItem(APP_THEME_STORAGE_KEY, theme.value)
    }
    applyThemeToDocument()
  }

  watch(theme, (): void => {
    applyThemeToDocument()
  })

  return { theme, initTheme, toggleTheme }
}
