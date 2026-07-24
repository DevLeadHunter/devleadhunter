/**
 * Date formatting used across the dashboard.
 *
 * Chaque fonction est nommée par ce qu'elle AFFICHE : un `formatDate` générique
 * obligeait à ouvrir le fichier pour savoir si la sortie portait l'heure, l'année
 * ou un mois en toutes lettres — il en existait onze versions différentes.
 * @module utils/date
 */

const LOCALE: string = 'fr-FR'

/**
 * Format an ISO date as `01/06/26 14:32`.
 * @param iso - ISO-8601 date string, or a falsy value for an unknown date.
 * @returns The formatted date, or an empty string when `iso` is falsy.
 */
export function formatCompactDateTime(iso: string | null | undefined): string {
  if (!iso) return ''
  return new Date(iso).toLocaleString(LOCALE, {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Format an ISO date as `01/06/2026`.
 * @param iso - ISO-8601 date string, or a falsy value for an unknown date.
 * @returns The formatted date, or an empty string when `iso` is falsy.
 */
export function formatNumericDate(iso: string | null | undefined): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(LOCALE)
}

/**
 * Format an ISO date as `01/06/2026 14:32`.
 * @param iso - ISO-8601 date string, or a falsy value for an unknown date.
 * @returns The formatted date, or an empty string when `iso` is falsy.
 */
export function formatNumericDateTime(iso: string | null | undefined): string {
  if (!iso) return ''
  return new Date(iso).toLocaleString(LOCALE, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Format an ISO date as `01/06 14:32` — day and month only, with the time.
 * @param iso - ISO-8601 date string, or a falsy value for an unknown date.
 * @returns The formatted date, or an empty string when `iso` is falsy.
 */
export function formatNumericDayMonthTime(iso: string | null | undefined): string {
  if (!iso) return ''
  return new Date(iso).toLocaleString(LOCALE, {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Format an ISO date as `1 juin 2026`, month abbreviated.
 * @param iso - ISO-8601 date string, or a falsy value for an unknown date.
 * @returns The formatted date, or an empty string when `iso` is falsy.
 */
export function formatShortMonthDate(iso: string | null | undefined): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(LOCALE, { day: 'numeric', month: 'short', year: 'numeric' })
}

/**
 * Format an ISO date as `1 juin 2026`, month spelled out.
 * @param iso - ISO-8601 date string, or a falsy value for an unknown date.
 * @returns The formatted date, or an empty string when `iso` is falsy.
 */
export function formatLongMonthDate(iso: string | null | undefined): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(LOCALE, { day: 'numeric', month: 'long', year: 'numeric' })
}

/**
 * Format an ISO date as `1 juin 2026 14:32`.
 * @param iso - ISO-8601 date string, or a falsy value for an unknown date.
 * @returns The formatted date, or an empty string when `iso` is falsy.
 */
export function formatShortMonthDateTime(iso: string | null | undefined): string {
  if (!iso) return ''
  return new Date(iso).toLocaleString(LOCALE, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Format an ISO date as `1 juin 14:32` — no year.
 * @param iso - ISO-8601 date string, or a falsy value for an unknown date.
 * @returns The formatted date, or an empty string when `iso` is falsy.
 */
export function formatShortMonthDayTime(iso: string | null | undefined): string {
  if (!iso) return ''
  return new Date(iso).toLocaleString(LOCALE, {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Format an ISO date as `01 juin` — day and month only.
 * @param iso - ISO-8601 date string, or a falsy value for an unknown date.
 * @returns The formatted date, or an empty string when `iso` is falsy.
 */
export function formatDayAndShortMonth(iso: string | null | undefined): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(LOCALE, { day: '2-digit', month: 'short' })
}
