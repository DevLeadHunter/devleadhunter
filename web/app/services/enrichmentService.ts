import { ApiClient } from './api'
import type { ScraperSidecarInfo } from '~/services/scraperSidecarService'
import { getScraperSidecarInfo, postToScraperSidecar } from '~/services/scraperSidecarService'

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

/** One candidate of the decision-maker cascade (debug / provenance display). */
export type ContactNameCandidate = {
  first: string | null
  last: string | null
  source: string
  confidence: number
  primary: boolean
  geo_confirmed: boolean
  provenance: string
}

export type EnrichmentPhotoLabel = {
  kind: string
  description: string
  dishes: string[]
  appeal: number
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
  photo_labels: Record<string, EnrichmentPhotoLabel>
  contact_first_name: string | null
  contact_last_name: string | null
  contact_gender: string | null
  contact_name_source: string | null
  contact_name_confidence: number | null
  contact_name_manual: boolean
  contact_name_status: string | null
  contact_name_provenance: string | null
  contact_siren: string | null
  proposed_first_name: string | null
  proposed_last_name: string | null
  proposed_gender: string | null
  proposed_source: string | null
  proposed_confidence: number | null
  proposed_provenance: string | null
  proposed_state: string | null
  name_candidates: ContactNameCandidate[]
  place_title: string | null
  place_city: string | null
  place_postal_code: string | null
  identity_check_status: string | null
  identity_check_detail: string | null
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

/** Enrichment fields carried by a rich prospect import (mirror of the server `EnrichmentData`). */
export type ImportedEnrichmentPayload = {
  logo_url?: string | null
  rating?: number | null
  reviews_count?: number | null
  description?: string | null
  photos?: string[]
  reviews?: EnrichmentReview[]
  opening_hours?: EnrichmentOpeningHours[]
  services?: string[]
  social_links?: Record<string, string>
  place_title?: string | null
  place_city?: string | null
  place_postal_code?: string | null
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

/** A prospect fed to the local bulk enrichment — the sidecar scrapes each one. */
export type BulkEnrichTarget = {
  id: number
  name: string
  city: string | null
  googleMapsUrl: string | null
  facebookUrl: string | null
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
   * Run (or re-run) enrichment for a prospect.
   *
   * In the desktop app the scraping happens locally — Google blocks datacenter
   * IPs, so it must leave from the user's own connection — and only the result
   * is posted for persistence. Without a sidecar the server scrapes as before.
   *
   * @param prospectId - Target prospect id.
   * @param businessName - Business name the scraper looks up.
   * @param city - City narrowing the lookup.
   * @param googleMapsUrl - Maps place URL anchoring the scrape on the exact listing.
   * @param facebookUrl - Facebook page URL used when the prospect has no Google listing.
   * @returns The refreshed enrichment record.
   */
  static async runProspectEnrichment(
    prospectId: number,
    businessName: string,
    city: string,
    googleMapsUrl: string = '',
    facebookUrl: string = '',
  ): Promise<ProspectEnrichment> {
    const scrapedData: unknown = businessName
      ? await postToScraperSidecar<unknown>(
          '/scraper/enrichment',
          {
            business_name: businessName,
            city: city || null,
            google_maps_url: googleMapsUrl || null,
            facebook_url: facebookUrl || null,
          },
          // The sidecar caps a scrape at 180s — a call still pending past that is wedged.
          { timeoutMs: 240_000 },
        )
      : null
    // `null` et non `{}` : chaque champ d'EnrichmentData a un défaut, donc un objet
    // vide passerait pour un scrape réussi et l'API cesserait de scraper elle-même.
    return ApiClient.post<ProspectEnrichment>(`/api/v1/prospects/${prospectId}/enrichment/run`, scrapedData)
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
   * Promote the « à confirmer » decision-maker name to the trusted contact.
   * @param prospectId - Target prospect id.
   * @returns The refreshed enrichment record (contact_* fields filled).
   */
  static async confirmContactProposal(prospectId: number): Promise<ProspectEnrichment> {
    return ApiClient.post<ProspectEnrichment>(`/api/v1/prospects/${prospectId}/enrichment/contact-proposal/confirm`, {})
  }

  /**
   * Reject the « à confirmer » name — the same identity is never re-proposed.
   * @param prospectId - Target prospect id.
   * @returns The refreshed enrichment record (proposal marked rejected).
   */
  static async rejectContactProposal(prospectId: number): Promise<ProspectEnrichment> {
    return ApiClient.post<ProspectEnrichment>(`/api/v1/prospects/${prospectId}/enrichment/contact-proposal/reject`, {})
  }

  /**
   * Enrich several prospects locally, through the desktop sidecar.
   *
   * Scraping leaves the user's own machine (residential IP), like the drawer:
   * datacenter VPS IPs are blocked by Google, so a server-side bulk enrichment
   * would return nothing. Each prospect is scraped one after another — a single
   * browser, never two Google searches at once — but persisting one prospect
   * overlaps the scraping of the next: faster than a strictly sequential run,
   * without degrading the collected data.
   *
   * @param targets - The prospects to enrich (already loaded by the list view).
   * @param onProgress - Called after each prospect is processed, for UI progress.
   * @returns Per-prospect results plus succeeded/failed counts.
   * @throws When no local sidecar is available (web build outside the desktop app).
   */
  static async runBulkEnrichment(
    targets: BulkEnrichTarget[],
    onProgress?: (completed: number, total: number) => void,
  ): Promise<BulkEnrichResult> {
    const sidecar: ScraperSidecarInfo | null = await getScraperSidecarInfo()
    if (!sidecar) {
      throw new Error(
        "L'enrichissement groupé s'exécute en local : lancez-le depuis l'application desktop " +
          '(le scraping doit partir de votre connexion, pas du serveur).',
      )
    }

    const total: number = targets.length
    const results: BulkEnrichItemResult[] = []
    let completed: number = 0

    /** Persist the scraped result; runs while the NEXT prospect is scraping. */
    const persist: (target: BulkEnrichTarget, scraped: unknown) => Promise<void> = async (
      target: BulkEnrichTarget,
      scraped: unknown,
    ): Promise<void> => {
      try {
        const record: ProspectEnrichment = await ApiClient.post<ProspectEnrichment>(
          `/api/v1/prospects/${target.id}/enrichment/run`,
          scraped,
        )
        results.push({ prospect_id: target.id, status: record.status, error: record.error_message })
      } catch (err: unknown) {
        results.push({ prospect_id: target.id, status: 'failed', error: err instanceof Error ? err.message : null })
      } finally {
        completed += 1
        onProgress?.(completed, total)
      }
    }

    // Pipeline à deux étages : au plus un scrape ET une persistance en vol à la fois.
    let pendingPersist: Promise<void> = Promise.resolve()
    for (const target of targets) {
      let scraped: unknown
      try {
        scraped = await postToScraperSidecar<unknown>(
          '/scraper/enrichment',
          {
            business_name: target.name,
            city: target.city,
            google_maps_url: target.googleMapsUrl,
            facebook_url: target.facebookUrl,
          },
          { timeoutMs: 240_000 },
        )
      } catch (err: unknown) {
        await pendingPersist
        results.push({ prospect_id: target.id, status: 'failed', error: err instanceof Error ? err.message : null })
        completed += 1
        onProgress?.(completed, total)
        continue
      }
      // La persistance précédente doit finir (≤ 1 en vol) avant d'en lancer une autre…
      await pendingPersist
      // …puis on lance celle-ci sans l'attendre : elle recouvre le scrape suivant.
      pendingPersist = persist(target, scraped)
    }
    await pendingPersist

    const order: Map<number, number> = new Map(
      targets.map((target: BulkEnrichTarget, index: number): [number, number] => [target.id, index]),
    )
    results.sort(
      (a: BulkEnrichItemResult, b: BulkEnrichItemResult): number =>
        (order.get(a.prospect_id) ?? 0) - (order.get(b.prospect_id) ?? 0),
    )
    const succeeded: number = results.filter(
      (result: BulkEnrichItemResult): boolean => result.status === 'completed',
    ).length
    return { results, succeeded, failed: total - succeeded, total }
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

  /**
   * Persist enrichment carried by a rich JSON import — no scraping involved.
   * Reuses the desktop "post an already-scraped result" endpoint, so the record
   * is marked completed and the decision-maker cascade + identity guard run.
   * @param prospectId - Target prospect id.
   * @param data - Enrichment fields read from the imported JSON.
   * @returns The persisted enrichment record.
   */
  static async applyImportedEnrichment(
    prospectId: number,
    data: ImportedEnrichmentPayload,
  ): Promise<ProspectEnrichment> {
    return ApiClient.post<ProspectEnrichment>(`/api/v1/prospects/${prospectId}/enrichment/run`, {
      source: 'import',
      ...data,
    })
  }
}
