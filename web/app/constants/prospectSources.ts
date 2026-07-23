/** Prospect sources, kept in sync with the backend `Source` enum (`api/enums/source.py`). */
import type { ProspectSource } from '~/types'

export type ProspectSourceOption = {
  value: ProspectSource | ''
  label: string
  description?: string
}

const PROSPECT_SOURCE_OPTIONS: ProspectSourceOption[] = [
  {
    value: 'auto',
    label: 'Auto (recommandé)',
    description: 'OSM + Pages Jaunes en parallèle + enrichissement email automatique',
  },
  {
    value: 'google',
    label: 'Google',
    description: 'Google Maps / Google Business (navigateur Chrome)',
  },
  {
    value: 'pagesjaunes',
    label: 'Pages Jaunes',
    description: 'Annuaire Pages Jaunes (navigateur Chrome)',
  },
  {
    value: 'osm',
    label: 'OpenStreetMap',
    description: 'OpenStreetMap via Overpass API (HTTP pur, rapide)',
  },
  {
    value: 'brightdata',
    label: 'BrightData',
    description: 'API BrightData Web Unlocker + SERP (sans navigateur)',
  },
]

/** Options of the search-job form, where the empty value lets the server pick the sources. */
export const PROSPECT_SOURCE_SEARCH_OPTIONS: ProspectSourceOption[] = [
  { value: '', label: 'Toutes les sources' },
  ...PROSPECT_SOURCE_OPTIONS,
]

const SOURCE_LABEL_MAP: Record<string, string> = Object.fromEntries(
  PROSPECT_SOURCE_OPTIONS.map((option) => [option.value, option.label]),
)

/**
 * Format a source slug for tables and badges.
 *
 * @param source - Backend source value.
 * @returns The display label, or the raw slug so an unknown future source degrades gracefully.
 */
export function formatProspectSource(source: string): string {
  return SOURCE_LABEL_MAP[source] ?? source
}
