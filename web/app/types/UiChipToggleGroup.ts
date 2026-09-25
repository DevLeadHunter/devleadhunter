import type { SelectFieldOption, SelectFieldValue } from '~/types/SelectField'

/** Props of the chip row; `label` names the group for assistive technologies. */
export type UiChipToggleGroupProps<TValue extends SelectFieldValue = string> = {
  options: SelectFieldOption<TValue>[]
  disabled?: boolean
  label?: string
}
