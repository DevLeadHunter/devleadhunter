import type { EnrichmentReview, EnrichmentOpeningHours } from '~/services/enrichmentService'

export type UiProspectEnrichmentProps = {
  prospectId: number | null
  open: boolean
}

export type EnrichmentForm = {
  rating: number | null
  reviews_count: number | null
  description: string
  photos: string[]
  services: string[]
  reviews: EnrichmentReview[]
  opening_hours: EnrichmentOpeningHours[]
  contact_first_name: string
  contact_last_name: string
}
