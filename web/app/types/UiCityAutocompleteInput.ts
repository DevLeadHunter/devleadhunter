import type { CitySuggestion } from '~/types/CityAutocompleteInput'

export type UiCityAutocompleteInputEmits = {
  'update:modelValue': [value: string]
  select: [suggestion: CitySuggestion]
}
