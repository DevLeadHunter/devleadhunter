/**
 * Option d'un composant SelectField.
 */
export type SelectFieldOption = {
  value: string
  label: string
}

/**
 * Props du composant SelectField.
 */
export type SelectFieldProps = {
  modelValue: string
  options: SelectFieldOption[]
}
