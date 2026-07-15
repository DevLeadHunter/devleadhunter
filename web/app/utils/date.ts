/**
 * Shared date formatting utilities.
 * @module utils/date
 */

/**
 * Format an ISO-8601 date string as a short French locale datetime.
 *
 * Example output: ``"01/06/26 14:32"``
 * @param iso - ISO-8601 date string (e.g. from a backend timestamp field).
 * @returns Formatted date string, or an empty string when ``iso`` is falsy.
 */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return ''
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
