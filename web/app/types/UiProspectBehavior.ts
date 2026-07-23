/**
 * Props du composant UiProspectBehavior.
 */
export type UiProspectBehaviorProps = {
  /** Identifiant du prospect. */
  prospectId: number | null
  /** Email du prospect (pour l'envoi de la relance personnalisée). */
  prospectEmail: string | null
  /** Nom du prospect (destinataire). */
  prospectName: string
  /** Indique si le drawer parent est ouvert (déclencheur de chargement). */
  open: boolean
}
