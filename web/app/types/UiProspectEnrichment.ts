import type { EnrichmentReview, EnrichmentOpeningHours } from '~/services/enrichmentService'
import type { ProspectCountry } from '~/types'

export type UiProspectEnrichmentProps = {
  prospectId: number | null
  open: boolean
  prospectName: string
  prospectCity: string
  prospectGoogleMapsUrl: string
  prospectFacebookUrl: string
  prospectCountry: ProspectCountry
}

export type EnrichmentForm = {
  rating: number | null
  reviews_count: number | null
  description: string
  logo_url: string
  photos: string[]
  services: string[]
  reviews: EnrichmentReview[]
  opening_hours: EnrichmentOpeningHours[]
  contact_first_name: string
  contact_last_name: string
  professional_license_label: string
  professional_license_number: string
}
