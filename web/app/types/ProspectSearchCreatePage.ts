import type { ProspectCountry } from '~/types'
import type { ProspectSearchChannel, ProspectSearchRegion, ProspectSearchValidationMode } from '~/types/ProspectSearch'
import type { SelectFieldOption } from '~/types/SelectField'

export type ProspectSearchStepKey = 'target' | 'zone' | 'criteria' | 'launch'

export type ProspectSearchStepDefinition = {
  key: ProspectSearchStepKey
  label: string
  hint: string
}

export type ProspectSearchFranceZone = 'mainland' | ProspectSearchRegion

export type ProspectSearchFormState = {
  trades: string[]
  country: ProspectCountry
  franceZone: ProspectSearchFranceZone
  cities: string[]
  countPerTrade: number
  channel: ProspectSearchChannel
  onlyWithoutWebsite: boolean
  useRegistries: boolean
  validationMode: ProspectSearchValidationMode
}

export type ProspectSearchRecapRow = {
  label: string
  value: string
  detail?: string
}

export type ProspectSearchWaveOptions = {
  wave: number
  labels: string[]
  options: SelectFieldOption[]
}
