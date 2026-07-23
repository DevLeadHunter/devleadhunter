import { ApiClient } from '~/services/api'

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

export class ProspectsService {
  /**
   *
   */
  static async enrichProspect(payload: ProspectEnrichPayload): Promise<ProspectCreatePayload> {
    return ApiClient.post<ProspectCreatePayload>(`${BASE_URL}/enrich`, payload)
  }

  /**
   *
   */
  static async searchProspectSuggestions(
    payload: ProspectSearchSuggestionsPayload,
  ): Promise<ProspectSearchSuggestion[]> {
    return ApiClient.post<ProspectSearchSuggestion[]>(`${BASE_URL}/search-suggestions`, payload)
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
   * Run a Lighthouse (PageSpeed Insights) audit on the prospect's existing website.
   * Slow call (30-60s) — the caller must show a loader.
   * @param prospectId - Identifiant du prospect à auditer.
   * @returns Le prospect avec son audit stocké.
   */
  static async runLighthouseAudit(prospectId: number): Promise<Prospect> {
    return ApiClient.post<Prospect>(`${BASE_URL}/${prospectId}/lighthouse-audit`, {})
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
   *
   */
  static async deleteProspect(prospectId: number): Promise<void> {
    await ApiClient.delete(`${BASE_URL}/${prospectId}`)
  }
}
