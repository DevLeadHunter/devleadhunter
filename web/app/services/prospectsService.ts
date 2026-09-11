import { ApiClient } from '~/services/api'
import { postToScraperSidecar } from '~/services/scraperSidecarService'

import type {
  Prospect,
  ProspectCreatePayload,
  ProspectUpdatePayload,
  ProspectEnrichPayload,
  ProspectSearchSuggestion,
  ProspectSearchSuggestionsPayload,
} from '~/types'

const BASE_URL: string = '/api/v1/prospects'

/**
 
 * Pré-remplit les champs d'un prospect depuis Google Maps.
 
 * @param payload - Nom d'entreprise, lien Google Maps et/ou ville.
 
 * @returns Les champs prospect pré-remplis.
 
 */

/**
 
 * Recherche des suggestions d'entreprises sur Google Maps.
 
 * @param payload - Requête de recherche et filtres optionnels.
 
 * @returns La liste des suggestions correspondantes.
 
 */

/**
 
 * Crée un prospect manuellement.
 
 * @param payload - Données du prospect à enregistrer.
 
 * @returns Le prospect créé.
 
 */

/**
 
 * Liste les prospects sauvegardés de l'utilisateur courant.
 
 * @returns Les prospects enregistrés.
 
 */

/**
 
 * Supprime un prospect par identifiant.
 
 * @param prospectId - Identifiant du prospect à supprimer.
 
 * @returns Une promesse résolue une fois la suppression effectuée.
 
 */

/** Lead temperature (hot/warm/cold) + score for one prospect. */
export type ProspectTemperature = {
  prospect_id: number
  temperature: string
  score: number
}

export type ProspectTemperaturesResponse = {
  items: ProspectTemperature[]
}

export class ProspectsService {
  /**
   *
   */
  static async enrichProspect(payload: ProspectEnrichPayload): Promise<ProspectCreatePayload> {
    // Desktop : le scraping part de l'IP résidentielle de l'utilisateur, pas du VPS.
    const local: ProspectCreatePayload | null = await postToScraperSidecar<ProspectCreatePayload>(
      '/scraper/enrich',
      payload,
    )
    return local ?? ApiClient.post<ProspectCreatePayload>(`${BASE_URL}/enrich`, payload)
  }

  /**
   *
   */
  static async searchProspectSuggestions(
    payload: ProspectSearchSuggestionsPayload,
  ): Promise<ProspectSearchSuggestion[]> {
    const local: ProspectSearchSuggestion[] | null = await postToScraperSidecar<ProspectSearchSuggestion[]>(
      '/scraper/search-suggestions',
      payload,
    )
    return local ?? ApiClient.post<ProspectSearchSuggestion[]>(`${BASE_URL}/search-suggestions`, payload)
  }

  /**
   *
   */
  static async createProspect(payload: ProspectCreatePayload): Promise<Prospect> {
    return ApiClient.post<Prospect>(BASE_URL, payload)
  }

  /**
   *
   */
  static async listProspects(): Promise<Prospect[]> {
    return ApiClient.get<Prospect[]>(BASE_URL)
  }

  /**
   * Fetch a single prospect by its identifier.
   * @param prospectId - Identifiant du prospect.
   * @returns Le prospect complet.
   */
  static async getProspect(prospectId: number): Promise<Prospect> {
    return ApiClient.get<Prospect>(`${BASE_URL}/${prospectId}`)
  }

  /**
   * Reserve a shared prospect for the current user (organization anti double-outreach).
   * @param prospectId - Identifiant du prospect à réserver.
   * @returns Le prospect avec sa réservation posée.
   */
  static async reserveProspect(prospectId: number): Promise<Prospect> {
    return ApiClient.post<Prospect>(`${BASE_URL}/${prospectId}/reserve`, {})
  }

  /**
   * Release the current reservation so another member can take the prospect.
   * @param prospectId - Identifiant du prospect à libérer.
   * @returns Le prospect libéré.
   */
  static async releaseProspect(prospectId: number): Promise<Prospect> {
    return ApiClient.delete<Prospect>(`${BASE_URL}/${prospectId}/reserve`)
  }

  /**
   * Stop (or resume) all outreach to a prospect (« ne plus contacter »).
   * Blocks campaigns + SMS and holds back the prospect's pending sends.
   * @param prospectId - Identifiant du prospect.
   * @param enabled - true pour arrêter tout contact, false pour ré-autoriser.
   * @param reason - Note optionnelle sur la raison de l'arrêt.
   * @returns Le prospect mis à jour.
   */
  static async setDoNotContact(prospectId: number, enabled: boolean, reason?: string | null): Promise<Prospect> {
    return ApiClient.post<Prospect>(`${BASE_URL}/${prospectId}/do-not-contact`, { enabled, reason: reason ?? null })
  }

  /**
   * Run a Lighthouse (PageSpeed Insights) audit on the prospect's existing website.
   * Slow call (30-60s) — the caller must show a loader.
   * @param prospectId - Identifiant du prospect à auditer.
   * @returns Le prospect avec son audit stocké.
   */
  static async runLighthouseAudit(prospectId: number): Promise<Prospect> {
    return ApiClient.post<Prospect>(`${BASE_URL}/${prospectId}/lighthouse-audit`, {})
  }

  /**
   * Fetch the hot/warm/cold temperature of several prospects in one call.
   * @param prospectIds - Identifiants des prospects à évaluer.
   * @returns La liste des températures (une entrée par prospect ayant de l'activité).
   */
  static async getProspectTemperatures(prospectIds: number[]): Promise<ProspectTemperaturesResponse> {
    return ApiClient.post<ProspectTemperaturesResponse>(`${BASE_URL}/temperatures`, { prospect_ids: prospectIds })
  }

  /**
   
   * Met à jour les champs d'un prospect existant.
   
   * @param prospectId - Identifiant du prospect à modifier.
   * @param payload - Champs à mettre à jour (partiels).
   * @returns Le prospect mis à jour.
   
   */
  static async updateProspect(prospectId: number, payload: ProspectUpdatePayload): Promise<Prospect> {
    return ApiClient.put<Prospect>(`${BASE_URL}/${prospectId}`, payload)
  }

  /**
   * Remplace la liste ordonnée des emails d'un prospect (le premier devient le principal).
   * Couvre en un seul appel le réordonnancement, l'ajout et la suppression.
   * @param prospectId - Identifiant du prospect.
   * @param emails - Liste ordonnée des emails ; le premier est le principal.
   * @returns Le prospect mis à jour.
   */
  static async updateProspectEmails(prospectId: number, emails: string[]): Promise<Prospect> {
    return ApiClient.put<Prospect>(`${BASE_URL}/${prospectId}/emails`, { emails })
  }

  /**
   * Remplace la liste ordonnée des numéros d'un prospect (le premier devient le principal).
   * Couvre en un seul appel le réordonnancement, l'ajout et la suppression.
   * @param prospectId - Identifiant du prospect.
   * @param phones - Liste ordonnée des numéros ; le premier est le principal.
   * @returns Le prospect mis à jour.
   */
  static async updateProspectPhones(prospectId: number, phones: string[]): Promise<Prospect> {
    return ApiClient.put<Prospect>(`${BASE_URL}/${prospectId}/phones`, { phones })
  }

  /**
   *
   */
  static async deleteProspect(prospectId: number): Promise<void> {
    await ApiClient.delete(`${BASE_URL}/${prospectId}`)
  }

  /**
   * Remember a Facebook page rejected by the search match filter (no email / has
   * a website), so future Facebook discoveries skip it instead of re-testing it.
   * @param pageUrl - Canonical Facebook page URL.
   * @param reason - Why the page is unusable.
   * @returns A promise resolved once the exclusion is stored.
   */
  static async excludeFacebookPage(pageUrl: string, reason: 'no_email' | 'has_website'): Promise<void> {
    await ApiClient.post<{ status: string }>(`${BASE_URL}/facebook-exclusions`, { page_url: pageUrl, reason })
  }
}
