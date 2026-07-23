/** Optional values pre-filled into the search form when the drawer opens. */
export type SearchProspectsPrefill = {
  category?: string
  city?: string
}

export type SearchProspectsDrawerProps = {
  open: boolean
  showBack: boolean
  prefill?: SearchProspectsPrefill | null
}

export type SearchFormState = {
  category: string
  city: string
  maxResults: number
  source: string
  skipDuplicates: boolean
  onlyWithoutWebsite: boolean
}
