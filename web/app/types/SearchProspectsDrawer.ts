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
