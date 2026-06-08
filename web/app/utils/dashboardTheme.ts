/**
 * Shared accent palette for the dashboard widgets.
 *
 * Hex values reuse the project's existing dark-theme accents so the new
 * dashboard stays visually consistent with the rest of the app. Components
 * apply them as inline styles (dynamic values) to avoid Tailwind JIT purge
 * issues with runtime-generated classes.
 */

/** Accent keys available to dashboard widgets. */
export type DashboardAccent = 'blue' | 'green' | 'amber' | 'violet' | 'red' | 'slate'

/** Accent key → hex color. */
export const ACCENT_HEX: Record<DashboardAccent, string> = {
  blue: '#58a6ff',
  green: '#3fb950',
  amber: '#e3b341',
  violet: '#bc8cff',
  red: '#ff7b72',
  slate: '#8b949e',
}

/**
 * Resolve a hex color for an accent key.
 * @param accent - Accent key.
 * @returns The matching hex color (falls back to blue).
 */
export function accentHex(accent: DashboardAccent): string {
  return ACCENT_HEX[accent] ?? ACCENT_HEX.blue
}

/**
 * Build an rgba() string from a 6-digit hex color and an alpha value.
 * @param hex - 6-digit hex color (e.g. "#58a6ff").
 * @param alpha - Alpha channel between 0 and 1.
 * @returns The rgba() CSS string.
 */
export function hexAlpha(hex: string, alpha: number): string {
  const value: string = hex.replace('#', '')
  const r: number = parseInt(value.slice(0, 2), 16)
  const g: number = parseInt(value.slice(2, 4), 16)
  const b: number = parseInt(value.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}
