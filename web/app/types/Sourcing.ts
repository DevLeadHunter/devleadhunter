/** A Réceptionniste IA target vertical, offered as a search preset. */
export type SourcingVertical = {
  key: string
  label: string
  wave: number
  search_terms: string[]
}

/** The search terms of one prospection wave, in catalog order. */
export type SourcingWavePreset = {
  wave: number
  labels: string[]
  searchTerms: string[]
}
