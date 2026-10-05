import type { SelectFieldOption, SelectFieldValue } from '~/types/SelectField'

export type UiChipFiltersProps<TValue extends SelectFieldValue = string> = {
  options: SelectFieldOption<TValue>[]
  label: string
}
