/**
 * Suggestion de ville renvoyée par l'API geo.api.gouv.fr.
 */
export interface CitySuggestion {
  /** Code INSEE de la commune (identifiant unique). */
  code: string
  /** Nom de la commune. */
  nom: string
  /** Numéro de département (ex : "69"). */
  codeDepartement?: string
  /** Codes postaux de la commune. */
  codesPostaux?: string[]
}

/**
 * Props du composant CityAutocompleteInput.
 */
export interface CityAutocompleteInputProps {
  /** Valeur du champ (v-model). */
  modelValue: string
  /** Placeholder de l'input. */
  placeholder?: string
  /** Attribut id de l'input (liaison label externe). */
  inputId?: string
  /** Champ requis (validation native du formulaire). */
  required?: boolean
  /** Affiche l'icône map-pin à gauche du champ. */
  showIcon?: boolean
}
