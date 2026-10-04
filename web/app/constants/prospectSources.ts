/** Prospect sources, kept in sync with the backend `Source` enum (`api/enums/source.py`). */
const PROSPECT_SOURCE_LABELS: Record<string, string> = {
  search: 'Recherche',
  auto: 'Auto',
  google: 'Google',
  pagesjaunes: 'Pages Jaunes',
  osm: 'OpenStreetMap',
  brightdata: 'BrightData',
  facebook: 'Facebook',
  manual: 'Ajout manuel',
}

/**
 * Format a source slug for tables and badges.
 *
 * @param source - Backend source value.
 * @returns The display label, or the raw slug so an unknown future source degrades gracefully.
 */
export function formatProspectSource(source: string): string {
  return PROSPECT_SOURCE_LABELS[source] ?? source
}
