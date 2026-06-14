import { api } from './api'

/** A single scraped review. */
export interface EnrichmentReview {
  author?: string
  text?: string
  rating?: number | null
}

/** A single opening-hours row. */
export interface EnrichmentOpeningHours {
  day?: string
  hours?: string
}

/** Rich enrichment data attached to a prospect. */
export interface ProspectEnrichment {
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
  error_message: string | null
  enriched_at: string | null
  created_at: string
  updated_at: string | null
}

/** Editable enrichment fields. */
export interface ProspectEnrichmentUpdate {
  logo_url?: string | null
  rating?: number | null
  reviews_count?: number | null
  description?: string | null
  photos?: string[]
  reviews?: EnrichmentReview[]
  opening_hours?: EnrichmentOpeningHours[]
  services?: string[]
  social_links?: Record<string, string>
}

/**
 * Fetch a prospect's enrichment data.
 * @param prospectId - Target prospect id.
 * @returns The enrichment record, or null when none exists yet.
 */
export async function getProspectEnrichment(prospectId: number): Promise<ProspectEnrichment | null> {
  try {
    return await api.get<ProspectEnrichment>(`/api/v1/prospects/${prospectId}/enrichment`)
  } catch {
    return null
  }
}

/**
 * Run (or re-run) enrichment scraping for a prospect.
 * @param prospectId - Target prospect id.
 * @returns The refreshed enrichment record.
 */
export async function runProspectEnrichment(prospectId: number): Promise<ProspectEnrichment> {
  return api.post<ProspectEnrichment>(`/api/v1/prospects/${prospectId}/enrichment/run`, {})
}

/** Per-prospect outcome of a bulk enrichment run. */
export interface BulkEnrichItemResult {
  prospect_id: number
  status: string
  error?: string | null
}

/** Aggregated result of a bulk enrichment run. */
export interface BulkEnrichResult {
  results: BulkEnrichItemResult[]
  succeeded: number
  failed: number
  total: number
}

/**
 * Enrich several prospects in one call (runs sequentially server-side).
 * @param prospectIds - Target prospect ids.
 * @returns Per-prospect results plus succeeded/failed counts.
 */
export async function runBulkEnrichment(prospectIds: number[]): Promise<BulkEnrichResult> {
  return api.post<BulkEnrichResult>('/api/v1/prospects/enrichment/bulk-run', { prospect_ids: prospectIds })
}

/**
 * Apply manual edits to a prospect's enrichment data.
 * @param prospectId - Target prospect id.
 * @param payload - Fields to update.
 * @returns The updated enrichment record.
 */
export async function updateProspectEnrichment(
  prospectId: number,
  payload: ProspectEnrichmentUpdate,
): Promise<ProspectEnrichment> {
  return api.patch<ProspectEnrichment>(`/api/v1/prospects/${prospectId}/enrichment`, payload)
}
