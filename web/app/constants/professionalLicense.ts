import type { ProspectCountry } from '~/types'
import type { RequiredProfessionalLicense } from '~/types/ProfessionalLicense'

/** The label a Québec license gets until the operator renames it. */
export const PROFESSIONAL_LICENSE_DEFAULT_LABEL: string = 'Licence RBQ'

/** Where a professional license stored on an enrichment came from, keyed by its API source. */
export const PROFESSIONAL_LICENSE_SOURCE_LABELS: Record<string, string> = {
  rbq_registry: 'Trouvée dans le registre RBQ',
  manual: 'Saisie manuelle',
}

/** The license a site must show, in the only countries whose law asks for one. */
export const REQUIRED_PROFESSIONAL_LICENSES: Partial<Record<ProspectCountry, RequiredProfessionalLicense>> = {
  CA: { label: PROFESSIONAL_LICENSE_DEFAULT_LABEL, numberExample: '5678-1234-01' },
  LU: { label: "Autorisation d'établissement", numberExample: '10078566/0' },
}
