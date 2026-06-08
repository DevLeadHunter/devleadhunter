/**
 * Props du composant UiProspectEnrichment.
 */
export interface UiProspectEnrichmentProps {
  /** Identifiant du prospect dont on charge l'enrichissement. */
  prospectId: number | null
  /** Indique si le drawer parent est ouvert (déclencheur de chargement paresseux). */
  open: boolean
}
