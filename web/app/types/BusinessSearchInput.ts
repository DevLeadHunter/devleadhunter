/**
 * Props du composant BusinessSearchInput.
 */
export type BusinessSearchInputProps = {
  /** Ville optionnelle pour affiner la recherche Google Maps. */
  city?: string
}

/**
 * Méthodes exposées par le composant BusinessSearchInput.
 */
export type BusinessSearchInputExpose = {
  /** Réinitialise le champ de recherche et les suggestions. */
  reset: () => void
}
