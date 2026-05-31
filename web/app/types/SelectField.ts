/**
 * Option d'un composant SelectField.
 */
export interface SelectFieldOption {
  value: string
  label: string
}

/**
 * Props du composant SelectField.
 */
export interface SelectFieldProps {
  modelValue: string
  options: SelectFieldOption[]
}
