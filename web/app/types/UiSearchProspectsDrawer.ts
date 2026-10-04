import type { ProspectCountry } from '~/types'
import type { ProspectSearchChannel } from '~/types/ProspectSearch'

/** Optional values pre-filled into the search form when the drawer opens. */
export type SearchProspectsPrefill = {
  category?: string
  city?: string
  country?: ProspectCountry
}

export type UiSearchProspectsDrawerProps = {
  open: boolean
  showBack: boolean
  prefill?: SearchProspectsPrefill | null
}

export type UiSearchProspectsDrawerEmits = {
  close: []
  back: []
}

export type ProspectSearchFormState = {
  trades: string[]
  country: ProspectCountry
  cities: string[]
  countPerTrade: number
  channel: ProspectSearchChannel
  onlyWithoutWebsite: boolean
  minimumRating: number | null
}
