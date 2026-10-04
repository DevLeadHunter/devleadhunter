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
 * Parse an API date string into a `Date`, reading zone-less values as UTC.
 *
 * The backend serialises naive UTC without an offset; left as-is `new Date()`
 * would read it as local time and shift every clock. Zoned values pass untouched.
 * @param iso - ISO-8601 date or date-time string.
 * @returns A `Date` at the correct instant.
 */
export function parseApiDate(iso: string): Date {
  const hasTime: boolean = iso.includes('T')
  const hasZone: boolean = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(iso)
  return new Date(hasTime && !hasZone ? `${iso}Z` : iso)
}

/**
 * Whole days left until an API date, never negative (a past date reads as 0).
 * @param iso - ISO-8601 date or date-time string.
 * @returns The number of days, rounded up.
 */
export function daysUntil(iso: string): number {
  const remainingMilliseconds: number = parseApiDate(iso).getTime() - Date.now()
  return Math.max(0, Math.ceil(remainingMilliseconds / (1000 * 60 * 60 * 24)))
}

/**
 * Format an ISO date as `01/06/26 14:32`.
 * @param iso - ISO-8601 date string, or a falsy value for an unknown date.
 * @returns The formatted date, or an empty string when `iso` is falsy.
 */
export function formatCompactDateTime(iso: string | null | undefined): string {
  if (!iso) return ''
  return parseApiDate(iso).toLocaleString(LOCALE, {
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
  return parseApiDate(iso).toLocaleDateString(LOCALE)
}

/**
 * Format an ISO date as `01/06/2026 14:32`.
 * @param iso - ISO-8601 date string, or a falsy value for an unknown date.
 * @returns The formatted date, or an empty string when `iso` is falsy.
 */
export function formatNumericDateTime(iso: string | null | undefined): string {
  if (!iso) return ''
  return parseApiDate(iso).toLocaleString(LOCALE, {
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
  return parseApiDate(iso).toLocaleString(LOCALE, {
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
  return parseApiDate(iso).toLocaleDateString(LOCALE, { day: 'numeric', month: 'short', year: 'numeric' })
}

/**
 * Format an ISO date as `1 juin 2026`, month spelled out.
 * @param iso - ISO-8601 date string, or a falsy value for an unknown date.
 * @returns The formatted date, or an empty string when `iso` is falsy.
 */
export function formatLongMonthDate(iso: string | null | undefined): string {
  if (!iso) return ''
  return parseApiDate(iso).toLocaleDateString(LOCALE, { day: 'numeric', month: 'long', year: 'numeric' })
}

/**
 * Format an ISO date as `1 juin 2026 14:32`.
 * @param iso - ISO-8601 date string, or a falsy value for an unknown date.
 * @returns The formatted date, or an empty string when `iso` is falsy.
 */
export function formatShortMonthDateTime(iso: string | null | undefined): string {
  if (!iso) return ''
  return parseApiDate(iso).toLocaleString(LOCALE, {
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
  return parseApiDate(iso).toLocaleString(LOCALE, {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Format an ISO date as `14:32:07` — the time alone, to the second.
 * @param iso - ISO-8601 date string, or a falsy value for an unknown date.
 * @returns The formatted time, or an empty string when `iso` is falsy.
 */
export function formatClockTime(iso: string | null | undefined): string {
  if (!iso) return ''
  return parseApiDate(iso).toLocaleTimeString(LOCALE, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

/**
 * Format an ISO date as `01 juin` — day and month only.
 * @param iso - ISO-8601 date string, or a falsy value for an unknown date.
 * @returns The formatted date, or an empty string when `iso` is falsy.
 */
export function formatDayAndShortMonth(iso: string | null | undefined): string {
  if (!iso) return ''
  return parseApiDate(iso).toLocaleDateString(LOCALE, { day: '2-digit', month: 'short' })
}

/**
 * Format an ISO date as a short relative label — `À l'instant`, `il y a 3 min`,
 * `il y a 2 h`, `Hier`, `il y a 4 jours`, then falls back to `01/06/2026`.
 * @param iso - ISO-8601 date string, or a falsy value for an unknown date.
 * @returns The relative label, or an empty string when `iso` is falsy.
 */
export function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const diffMinutes: number = Math.floor((Date.now() - parseApiDate(iso).getTime()) / 60000)
  if (diffMinutes < 1) return "À l'instant"
  if (diffMinutes < 60) return `il y a ${diffMinutes} min`
  const diffHours: number = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `il y a ${diffHours} h`
  const diffDays: number = Math.floor(diffHours / 24)
  if (diffDays === 1) return 'Hier'
  if (diffDays < 7) return `il y a ${diffDays} jours`
  return formatNumericDate(iso)
}

/**
 * Format a date as the value of a `datetime-local` input (local time, minute precision).
 * @param moment - The date to format.
 * @returns The `YYYY-MM-DDTHH:mm` local string.
 */
export function toDatetimeLocalValue(moment: Date): string {
  const pad: (value: number) => string = (value: number): string => String(value).padStart(2, '0')
  return `${moment.getFullYear()}-${pad(moment.getMonth() + 1)}-${pad(moment.getDate())}T${pad(moment.getHours())}:${pad(moment.getMinutes())}`
}

/**
 * Read a `datetime-local` input value as a moment, only when it lies in the future.
 * @param value - The `YYYY-MM-DDTHH:mm` local string.
 * @returns The date, or `null` when empty, invalid or not in the future.
 */
export function parseFutureDatetimeLocalValue(value: string): Date | null {
  if (!value) return null
  const moment: Date = new Date(value)
  if (Number.isNaN(moment.getTime()) || moment.getTime() <= Date.now()) return null
  return moment
}

/**
 * Format a planned send time relative to today: `aujourd'hui à 18:30`, `demain à 11:00`, `lundi 5 oct. à 09:00`.
 * @param moment - The planned time.
 * @returns The label, in local time.
 */
export function formatScheduledMoment(moment: Date): string {
  const time: string = moment.toLocaleTimeString(LOCALE, { hour: '2-digit', minute: '2-digit' })
  const startOfToday: Date = new Date()
  startOfToday.setHours(0, 0, 0, 0)
  const startOfMoment: Date = new Date(moment)
  startOfMoment.setHours(0, 0, 0, 0)
  const dayOffset: number = Math.round((startOfMoment.getTime() - startOfToday.getTime()) / (1000 * 60 * 60 * 24))
  if (dayOffset === 0) return `aujourd'hui à ${time}`
  if (dayOffset === 1) return `demain à ${time}`
  const day: string = moment.toLocaleDateString(LOCALE, { weekday: 'long', day: 'numeric', month: 'short' })
  return `${day} à ${time}`
}
