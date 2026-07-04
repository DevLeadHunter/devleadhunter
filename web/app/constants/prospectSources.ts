/**
 * Prospect source options aligned with the backend ``Source`` enum
 * (``api/enums/source.py``) and the ``/api/v1/sources`` endpoint.
 * @module prospectSources
 */
import type { ProspectSource } from '~/types'

/** Sentinel value for "all sources" in filter selects. */
export const ALL_SOURCES_VALUE = 'all' as const

/** A single selectable source option used in dropdowns and filter chips. */
export interface ProspectSourceOption {
  /** Source enum value sent to the API. */
  value: ProspectSource | typeof ALL_SOURCES_VALUE | ''
  /** French display label shown in the UI. */
  label: string
  /** Short description of the source for tooltips / help text. */
  description?: string
}

/**
 * All prospect sources registered in the backend scraper service.
 *
 * Keep in sync with:
 * - ``api/enums/source.py``  (Python ``Source`` enum)
 * - ``api/schemas/sources.py``
 * @remarks
 * - ``auto``        launches OSM + Pages Jaunes in parallel then enriches emails — recommended default
 * - ``brightdata``  calls the BrightData HTTP API (no browser) — requires ``BRIGHTDATA_API_TOKEN``
 */
export const PROSPECT_SOURCE_OPTIONS: ProspectSourceOption[] = [
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
  {
    value: 'mock',
    label: 'Mock (Test)',
    description: 'Données fictives pour le développement local',
  },
]

/**
 * Options for the search-job form (empty string means "all sources — let the server decide").
 * @returns Array with a leading "all sources" sentinel followed by all individual sources.
 */
export const PROSPECT_SOURCE_SEARCH_OPTIONS: ProspectSourceOption[] = [
  { value: '', label: 'Toutes les sources' },
  ...PROSPECT_SOURCE_OPTIONS,
]

/**
 * Options for the my-prospects filter panel (uses the explicit ``"all"`` enum value).
 * @returns Array with a leading "all sources" option followed by all individual sources.
 */
export const PROSPECT_SOURCE_FILTER_OPTIONS: ProspectSourceOption[] = [
  { value: ALL_SOURCES_VALUE, label: 'Toutes les sources' },
  ...PROSPECT_SOURCE_OPTIONS,
]

/** Internal lookup map: source value → display label. */
const SOURCE_LABEL_MAP: Record<string, string> = Object.fromEntries(
  PROSPECT_SOURCE_OPTIONS.map((opt) => [opt.value, opt.label]),
)

/**
 * Format a source slug for display in tables and badges.
 *
 * Falls back to the raw slug when the source is not in the registry,
 * so unknown future sources degrade gracefully.
 * @param {string} source - Backend source value (e.g. ``"auto"``, ``"pagesjaunes"``).
 * @returns {string} Human-readable label (e.g. ``"Auto (recommandé)"``).
 * @example
 * formatProspectSource('auto')        // → "Auto (recommandé)"
 * formatProspectSource('pagesjaunes') // → "Pages Jaunes"
 * formatProspectSource('unknown')     // → "unknown"
 */
export function formatProspectSource(source: string): string {
  return SOURCE_LABEL_MAP[source] ?? source
}
