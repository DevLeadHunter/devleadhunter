/** Optional values pre-filled into the search form when the drawer opens. */
export interface SearchProspectsPrefill {
  /** Trade to search for. */
  category?: string
  /** City to search in. */
  city?: string
}

/**
 * Props for the UiSearchProspectsDrawer component.
 */
export interface SearchProspectsDrawerProps {
  /** Whether the drawer is open. */
  open: boolean
  /** Whether to show the "back" affordance (drawer stacked on another). */
  showBack: boolean
  /** Values applied to the form on open (e.g. « Prospecter » from the coverage map). */
  prefill?: SearchProspectsPrefill | null
}
