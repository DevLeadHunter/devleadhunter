import type { SelectFieldOption, SelectFieldValue } from '~/types/SelectField'

export type UiChipToggleGroupProps<TValue extends SelectFieldValue = string> = {
  options: SelectFieldOption<TValue>[]
  disabled?: boolean
}
