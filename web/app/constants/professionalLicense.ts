/** The label a Québec license gets until the operator renames it. */
export const PROFESSIONAL_LICENSE_DEFAULT_LABEL: string = 'Licence RBQ'

/** Where a professional license stored on an enrichment came from, keyed by its API source. */
export const PROFESSIONAL_LICENSE_SOURCE_LABELS: Record<string, string> = {
  rbq_registry: 'Trouvée dans le registre RBQ',
  manual: 'Saisie manuelle',
}
