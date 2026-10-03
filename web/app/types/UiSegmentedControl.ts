import type { SelectFieldOption, SelectFieldValue } from '~/types/SelectField'

export type UiSegmentedControlProps<TValue extends SelectFieldValue = string> = {
  options: SelectFieldOption<TValue>[]
  label: string
}
