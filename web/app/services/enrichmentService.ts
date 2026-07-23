import { ApiClient } from './api'

/** A single scraped review. */
export type EnrichmentReview = {
  author?: string
  text?: string
  rating?: number | null
}

/** A single opening-hours row. */
export type EnrichmentOpeningHours = {
  day?: string
  hours?: string
}

/** Rich enrichment data attached to a prospect. */
export type ProspectEnrichment = {
  id: number
  prospect_id: number
  status: string
  source: string | null
  logo_url: string | null
  rating: number | null
  reviews_count: number | null
  description: string | null
  photos: string[]
  reviews: EnrichmentReview[]
  opening_hours: EnrichmentOpeningHours[]
  services: string[]
  social_links: Record<string, string>
  contact_first_name: string | null
  contact_last_name: string | null
  contact_gender: string | null
  contact_name_source: string | null
  contact_name_confidence: number | null
  contact_name_manual: boolean
  error_message: string | null
  enriched_at: string | null
  created_at: string
  updated_at: string | null
}

export type ProspectEnrichmentUpdate = {
  logo_url?: string | null
  rating?: number | null
  reviews_count?: number | null
  description?: string | null
  photos?: string[]
  reviews?: EnrichmentReview[]
  opening_hours?: EnrichmentOpeningHours[]
  services?: string[]
  social_links?: Record<string, string>
  contact_first_name?: string | null
  contact_last_name?: string | null
}

/** Per-prospect outcome of a bulk enrichment run. */
export type BulkEnrichItemResult = {
  prospect_id: number
  status: string
  error?: string | null
}

/** Aggregated result of a bulk enrichment run. */
export type BulkEnrichResult = {
  results: BulkEnrichItemResult[]
  succeeded: number
  failed: number
  total: number
}

export class EnrichmentService {
  /**
   * Fetch a prospect's enrichment data.
   * @param prospectId - Target prospect id.
   * @returns The enrichment record, or null when none exists yet.
   */
  static async getProspectEnrichment(prospectId: number): Promise<ProspectEnrichment | null> {
    try {
      return await ApiClient.get<ProspectEnrichment>(`/api/v1/prospects/${prospectId}/enrichment`)
    } catch {
      return null
    }
  }

  /**
   * Run (or re-run) enrichment scraping for a prospect.
   * @param prospectId - Target prospect id.
   * @returns The refreshed enrichment record.
   */
  static async runProspectEnrichment(prospectId: number): Promise<ProspectEnrichment> {
    return ApiClient.post<ProspectEnrichment>(`/api/v1/prospects/${prospectId}/enrichment/run`, {})
  }

  /**
   * (Re)run only the decision-maker name resolution for a prospect.
   * @param prospectId - Target prospect id.
   * @returns The refreshed enrichment record (contact_* fields updated).
   */
  static async resolveProspectContact(prospectId: number): Promise<ProspectEnrichment> {
    return ApiClient.post<ProspectEnrichment>(`/api/v1/prospects/${prospectId}/enrichment/resolve-contact`, {})
  }

  /**
   * Enrich several prospects in one call (runs sequentially server-side).
   * @param prospectIds - Target prospect ids.
   * @returns Per-prospect results plus succeeded/failed counts.
   */
  static async runBulkEnrichment(prospectIds: number[]): Promise<BulkEnrichResult> {
    return ApiClient.post<BulkEnrichResult>('/api/v1/prospects/enrichment/bulk-run', { prospect_ids: prospectIds })
  }

  /**
   * Apply manual edits to a prospect's enrichment data.
   * @param prospectId - Target prospect id.
   * @param payload - Fields to update.
   * @returns The updated enrichment record.
   */
  static async updateProspectEnrichment(
    prospectId: number,
    payload: ProspectEnrichmentUpdate,
  ): Promise<ProspectEnrichment> {
    return ApiClient.patch<ProspectEnrichment>(`/api/v1/prospects/${prospectId}/enrichment`, payload)
  }
}
