/**
 * Prospect source options aligned with backend `Source` enum and `/api/v1/sources`.
 */
import type { ProspectSource } from '~/types'

/** Sentinel value for "all sources" in filter selects. */
export const ALL_SOURCES_VALUE = 'all' as const

export interface ProspectSourceOption {
  /** Source enum value sent to the API. */
  value: ProspectSource | typeof ALL_SOURCES_VALUE | ''
  /** French display label. */
  label: string
}

/**
 * All prospect sources registered in the backend scraper service.
 * Keep in sync with `api/enums/source.py` and `api/schemas/sources.py`.
 */
export const PROSPECT_SOURCE_OPTIONS: ProspectSourceOption[] = [
  { value: 'google', label: 'Google' },
  { value: 'pagesjaunes', label: 'Pages Jaunes' },
  { value: 'yelp', label: 'Yelp' },
  { value: 'osm', label: 'OpenStreetMap' },
  { value: 'mock', label: 'Mock (Test)' },
]

/** Options for search job form (empty string = all sources). */
export const PROSPECT_SOURCE_SEARCH_OPTIONS: ProspectSourceOption[] = [
  { value: '', label: 'Toutes les sources' },
  ...PROSPECT_SOURCE_OPTIONS,
]

/** Options for my-prospects filter (includes explicit "all"). */
export const PROSPECT_SOURCE_FILTER_OPTIONS: ProspectSourceOption[] = [
  { value: ALL_SOURCES_VALUE, label: 'Toutes les sources' },
  ...PROSPECT_SOURCE_OPTIONS,
]

const SOURCE_LABEL_MAP: Record<string, string> = Object.fromEntries(
  PROSPECT_SOURCE_OPTIONS.map((opt) => [opt.value, opt.label]),
)

/**
 * Format a source slug for display in tables and badges.
 * @param source - Backend source value.
 * @returns Human-readable label.
 */
export function formatProspectSource(source: string): string {
  return SOURCE_LABEL_MAP[source] ?? source
}
