import type { SelectFieldValue } from '~/types/SelectField'

export type UiRadioCardOption<TValue extends SelectFieldValue = string> = {
  value: TValue
  label: string
  description: string
  icon: string
}

export type UiRadioCardGroupProps<TValue extends SelectFieldValue = string> = {
  options: UiRadioCardOption<TValue>[]
  labelledBy: string
}
